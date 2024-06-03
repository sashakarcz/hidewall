resource "linode_instance" "hidewall-node" {
  label      = var.label
  region     = var.region
  type       = var.type
  tags       = var.tags
  private_ip = true
  image      = "linode/debian12"
  root_pass  = var.root_pass
  swap_size  = 512
}
