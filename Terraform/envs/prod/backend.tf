#terraform {
#    backend "s3" {
#        bucket        = "terraform-state"
#        key           = "terraform.tfstate"
#        region        = "us-east-1"
#        endpoints     = { s3 = "https://us-ord-1.linodeobjects.com" }
#        profile       = "linode-s3"
#        skip_requesting_account_id = true
#        skip_credentials_validation = true
#        skip_metadata_api_check     = true
#        use_path_style              = true
#    }
#}
