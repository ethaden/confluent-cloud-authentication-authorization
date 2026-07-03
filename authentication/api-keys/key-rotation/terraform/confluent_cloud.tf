resource "confluent_service_account" "example_service_account" {
  display_name = "${var.service_account_name}"
  description  = "Service Account Example E"
}

locals {
  api_key_life_time_minutes = floor(provider::time::duration_parse(var.api_key_lifetime).minutes)
  api_key_overlap_time_minutes = floor(provider::time::duration_parse(var.api_key_overlap_time).minutes)
}

resource "time_static" "first_run" {
}

# This is the rotation cycle for the first API key.
# In this demo we assume that the corresponding key already exists for some time while
# the second key is new.

resource "time_rotating" "api_key_rotation_key1" {
  rotation_minutes = local.api_key_life_time_minutes
  # Do NOT use a "time_static" resource here. This would fix the timestamp in the base field "rfc3339" forever and render time-based rotation impossible
  # If using the "timestamp()" method instead, the field "rfc3339" will only be populated with the current timestamp during creation.
  # Whenever the rotation happens, the field will be updated properly
  rfc3339 = timestamp()
}

resource "time_static" "api_key_rotation_key1" {
  rfc3339 = time_rotating.api_key_rotation_key1.rotation_rfc3339
}

resource "time_rotating" "api_key_rotation_key2" {
  rotation_minutes = local.api_key_life_time_minutes
  # Do NOT use a "time_static" resource here. This would fix the timestamp in the base field "rfc3339" forever and render time-based rotation impossible
  # If using the "timestamp()" method instead, the field "rfc3339" will only be populated with the current timestamp during creation.
  # Whenever the rotation happens, the field will be updated properly.
  # Note: We postpone the rotation of this second key by (api_key_lifetime-api_key_overlap_time) by chosing a date in the future.
  rfc3339 = timeadd(timeadd(timestamp(), var.api_key_lifetime), "-${var.api_key_overlap_time}")
}

resource "time_static" "api_key_rotation_key2" {
  rfc3339 = time_rotating.api_key_rotation_key2.rotation_rfc3339
}

resource "confluent_api_key" "example_api_key_1" {
  display_name = "${var.service_account_name}_api_key_1"
  description  = "Example API Key 1, owned by '${var.service_account_name}' service account"
  owner {
    id          = confluent_service_account.example_service_account.id
    api_version = confluent_service_account.example_service_account.api_version
    kind        = confluent_service_account.example_service_account.kind
  }

  managed_resource {
    id          = "global"
    api_version = "global/v1"
    kind        = "Global"
  }

  lifecycle {
    prevent_destroy = false
    replace_triggered_by = [time_static.api_key_rotation_key1]
  }
}

resource "confluent_api_key" "example_api_key_2" {
  display_name = "${var.service_account_name}_api_key_2"
  description  = "Example API Key 2, owned by '${var.service_account_name}' service account"
  owner {
    id          = confluent_service_account.example_service_account.id
    api_version = confluent_service_account.example_service_account.api_version
    kind        = confluent_service_account.example_service_account.kind
  }

  managed_resource {
    id          = "global"
    api_version = "global/v1"
    kind        = "Global"
  }

  lifecycle {
    prevent_destroy = false
    replace_triggered_by = [time_static.api_key_rotation_key2]
  }
}

output "example_api_key_1" {
  value = nonsensitive("Key: ${confluent_api_key.example_api_key_1.id}\n Secret: ${confluent_api_key.example_api_key_1.secret}\n Valid until: ${formatdate("DD MMM YYYY hh:mm ZZZ", time_static.api_key_rotation_key1.rfc3339)}")
}

output "example_api_key_2" {
  value = nonsensitive("Key: ${confluent_api_key.example_api_key_2.id}\n Secret: ${confluent_api_key.example_api_key_2.secret}\n Valid until: ${formatdate("DD MMM YYYY hh:mm ZZZ", time_static.api_key_rotation_key2.rfc3339)}")
}


# Enable for debugging
#output "api_key_rotation_key1" {
#  value = time_rotating.api_key_rotation_key1
#}

# Enable for debugging
#output "api_key_rotation_key2" {
#  value = time_rotating.api_key_rotation_key2
#}

