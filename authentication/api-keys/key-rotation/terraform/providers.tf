terraform {
  required_providers {
    confluent = {
      source = "confluentinc/confluent"
      # we are using the latest version by leaving the next line commented. For production, fix the version!
      #version = "2.00.0"
    }
    time = {
      source  = "hashicorp/time"
      version = "~> 0.14"
    }
  }
}

provider "confluent" {
  cloud_api_key    = var.confluent_cloud_api_key
  cloud_api_secret = var.confluent_cloud_api_secret
}
