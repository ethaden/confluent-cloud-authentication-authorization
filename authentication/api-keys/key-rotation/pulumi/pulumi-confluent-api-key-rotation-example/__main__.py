import datetime
import os
import pulumi
import pulumi_confluentcloud as confluentcloud
import pulumiverse_time as time

config = pulumi.Config()

# ------------------------------------------------------------------------------
# 1. Dual-Authentication Strategy Validation
# ------------------------------------------------------------------------------
has_oauth_config = config.get_object("oauth") is not None
has_env_api_keys = (
    os.getenv("CONFLUENT_CLOUD_API_KEY") is not None and 
    os.getenv("CONFLUENT_CLOUD_API_SECRET") is not None
)

if not has_oauth_config and not has_env_api_keys:
    raise RuntimeError(
        "Authentication Error: No valid Confluent Cloud credentials found via ESC or Local Env."
    )

if has_oauth_config:
    tenant_id = ""
    identity_pool_id = ""
    entra_client_id = ""
    entra_client_secret = ""
    default_entra_provider = confluentcloud.Provider(
        "confluentcloud",
        oauth=confluentcloud.ProviderOauthArgs(
            oauth_identity_pool_id=identity_pool_id,
            oauth_external_client_id=entra_client_id,
            oauth_external_client_secret=entra_client_secret,
            oauth_external_token_url=f"https://microsoftonline.com{tenant_id}/oauth2/v2.0/token",
            oauth_external_token_scope=f"api://{entra_client_id}/.default"
        )
    )

# Fetch the list array of keys to process from Pulumi.dev.yaml
api_keys_list = config.require_object("apiKeys")

# Capture the absolute current execution timestamp in UTC
now = datetime.datetime.now(datetime.timezone.utc)
# For testing
#now = datetime.datetime.fromisoformat("2027-03-09T14:33:00Z")

# ------------------------------------------------------------------------------
# 2. Dynamic Argument Construction Mapping Helper
# ------------------------------------------------------------------------------
def build_managed_resource_args(scope: str, env_id: str = None, target_id: str = None) -> confluentcloud.ApiKeyManagedResourceArgs:
    scope = scope.upper()
    if scope == "CLOUD":
        return None
    if scope == "GLOBAL":
        return confluentcloud.ApiKeyManagedResourceArgs(
            id="global",
            api_version="global/v1",
            kind="Global"
        )
    if scope == "TABLEFLOW":
        return confluentcloud.ApiKeyManagedResourceArgs(
            id="tableflow",
            api_version="tableflow/v1",
            kind="Tableflow"
        )
    elif scope == "KAFKA":
        if env_id is None:
            raise ValueError(f"Environment ID is required when setting up '{scope}'")
        return confluentcloud.ApiKeyManagedResourceArgs(
            id=target_id,
            api_version="cmk/v2",
            kind="Cluster",
            environment=confluentcloud.ApiKeyManagedResourceEnvironmentArgs(id=env_id)
        )
    elif scope == "SCHEMA_REGISTRY":
        if env_id is None:
            raise ValueError(f"Environment ID is required when setting up '{scope}'")
        return confluentcloud.ApiKeyManagedResourceArgs(
            id=target_id,
            api_version="srcm/v2",
            kind="Cluster",
            environment=confluentcloud.ApiKeyManagedResourceEnvironmentArgs(id=env_id)
        )
    elif scope == "FLINK":
        if env_id is None:
            raise ValueError(f"Environment ID is required when setting up '{scope}'")
        return confluentcloud.ApiKeyManagedResourceArgs(
            id=target_id,
            api_version="fcpm/v2",
            kind="Region",
            environment=confluentcloud.ApiKeyManagedResourceEnvironmentArgs(id=env_id)
        )
    elif scope == "KSQLDB":
        if env_id is None:
            raise ValueError(f"Environment ID is required when setting up '{scope}'")
        return confluentcloud.ApiKeyManagedResourceArgs(
            id=target_id,
            api_version="ksqldbcm/v2",
            kind="Cluster",
            environment=confluentcloud.ApiKeyManagedResourceEnvironmentArgs(id=env_id)
        )
    else:
        raise ValueError(f"Unsupported resource scope targeting criteria: '{scope}'")

# ------------------------------------------------------------------------------
# 3. Multi-Key Processing Engine Loop
# ------------------------------------------------------------------------------
all_exported_outputs = {}

for key_def in api_keys_list:
    key_name = key_def.get("name")
    scope = key_def.get("scope", "GLOBAL").upper()
    target_id = key_def.get("targetResourceId")
    
    validity_days = int(key_def.get("validityDays", 180))
    overlap_days = int(key_def.get("overlapDays", 7))
    
    # Enforce mandatory per-key parameters
    env_id = key_def.get("confluentEnvironmentId", None)
    owner_id = key_def.get("ownerId")
    if not owner_id:
        raise ValueError(f"Key configuration '{key_name}' is missing the required 'ownerId' property.")

    owner_kind = key_def.get("ownerKind")
    if not owner_kind in ["ServiceAccount", "User"]:
        raise ValueError(f"Key profile '{key_name}' requires a 'owner_kind' to be either 'ServiceAccount' or 'User'.")

    # Validation constraint checks
    requires_id = ["KAFKA", "SCHEMA_REGISTRY", "FLINK", "KSQLDB"]
    if scope in requires_id and not target_id:
        raise ValueError(f"Key profile '{key_name}' requires a 'targetResourceId' for scope context '{scope}'.")

    # --- Localized Time Calculation Matrix ---
    # Extract the custom anchor date for this specific key profile
    epoch_start_str = key_def.get("epochStartDate") or "2026-01-01T00:00:00Z"
    epoch_start = datetime.datetime.fromisoformat(epoch_start_str.replace("Z", "+00:00"))
    
    days_since_epoch = (now - epoch_start).days
    if days_since_epoch < 0:
        raise ValueError(f"Key configuration '{key_name}' has an 'epochStartDate' set in the future.")

    days_into_current_cycle = days_since_epoch % validity_days
    current_cycle_index = days_since_epoch // validity_days
    
    primary_slot = "A" if (current_cycle_index % 2 == 0) else "B"
    # Overlap is at the end of each cycle
    is_in_overlap_window = validity_days - days_into_current_cycle < overlap_days

    # Define unique names for this key's rotation stateful clocks
    trigger_a_name = f"rot-trigger-{key_name}-a"
    trigger_b_name = f"rot-trigger-{key_name}-b"

    rotation_trigger_a = time.Rotating(
        trigger_a_name,
        rotation_days=validity_days * 2,
        rfc3339=epoch_start_str
    )

    rfc3339_b = (epoch_start + datetime.timedelta(days=validity_days-overlap_days)).isoformat().replace("+00:00", "Z")
    rotation_trigger_b = time.Rotating(
        trigger_b_name,
        rotation_days=validity_days * 2,
        rfc3339=rfc3339_b
    )

    # Isolated factory helper function using explicitly passed scope parameters
    # to protect against Python loop variable closure trapping.
    def create_api_key_resource(
        slot: str, 
        trigger_obj: time.Rotating, 
        resolved_env_id: str, 
        owner_id: str,
        resolved_key_name: str
    ) -> confluentcloud.ApiKey:
        full_display_name = f"{resolved_key_name}-{scope.lower()}-{slot.lower()}"
        return confluentcloud.ApiKey(
            f"api-key-{resolved_key_name}-{slot.lower()}",
            display_name=full_display_name,
            owner=confluentcloud.ApiKeyOwnerArgs(
                id=owner_id,
                api_version="iam/v2",
                kind=owner_kind,
            ),
            managed_resource=build_managed_resource_args(scope, resolved_env_id, target_id),
            opts=pulumi.ResourceOptions(
                replace_on_changes=["id", "managed_resource"],
                depends_on=[trigger_obj]
            )
        )

    api_key_a = None
    api_key_b = None

    if primary_slot == "A" or (primary_slot == "B" and is_in_overlap_window):
        api_key_a = create_api_key_resource("A", rotation_trigger_a, env_id, owner_id, key_name)

    if primary_slot == "B" or (primary_slot == "A" and is_in_overlap_window):
        api_key_b = create_api_key_resource("B", rotation_trigger_b, env_id, owner_id, key_name)

    # Structural Assignment & Resolution mapping
    if primary_slot == "A":
        primary_key_resource = api_key_a
        secondary_key_resource = api_key_b
    else:
        primary_key_resource = api_key_b
        secondary_key_resource = api_key_a

    # Construct clean nested JSON payload outputs for our consumer systems
    key_output_struct = {
        "primary_id": primary_key_resource.id if primary_key_resource else None,
        "primary_secret": primary_key_resource.secret if primary_key_resource else None,
        "secondary_active": is_in_overlap_window and secondary_key_resource is not None,
        "secondary_id": secondary_key_resource.id if (secondary_key_resource and is_in_overlap_window) else None,
        "secondary_secret": secondary_key_resource.secret if (secondary_key_resource and is_in_overlap_window) else None,
    }
    
    all_exported_outputs[key_name] = key_output_struct

# Final structured multi-key export output mapping
pulumi.export("confluent_keys", all_exported_outputs)
