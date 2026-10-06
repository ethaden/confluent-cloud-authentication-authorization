
# Recommendation: Overwrite the default in tfvars or stick with the automatic default
variable "confluent_cloud_api_key" {
  type        = string
  default     = null
  description = "Confluent Cloud API Key. This setup uses the environment variable CONFLUENT_CLOUD_API_KEY if this variable is not set"
}

variable "confluent_cloud_api_secret" {
  type        = string
  default     = null
  description = "Confluent Cloud API Secret. This setup uses the environment variable CONFLUENT_CLOUD_API_SECRET if this variable is not set"
  sensitive   = true
}

variable "generated_files_path" {
    description = "The main path to write generated files to"
    type = string
    default = "./generated"
}

variable "service_account_name" {
    type = string
    description = "Name of a service account"
}

# For this demo, we rotate keys, keys have a lifetime of 5 minutes. Set to larger value in practice!
variable "api_key_lifetime" {
    type = string
    default = "20m"
    description = "The desired lifetime of an AP key as a duration (https://developer.hashicorp.com/terraform/language/functions/timeadd#duration)"
}

# This specifies the time overlap when a older key is still valid while a newer key is already available
variable "api_key_overlap_time" {
    type = string
    default = "2m"
    description = "The desired overlap time of an AP keys as a duration (https://developer.hashicorp.com/terraform/language/functions/timeadd#duration)"
}
