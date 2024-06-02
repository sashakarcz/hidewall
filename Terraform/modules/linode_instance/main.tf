# modules/linode_instance/main.tf
resource "linode_instance" "hidewall-node" {
  label      = var.label
  region     = var.region
  type       = var.type
  tags       = var.tags
  private_ip = true
}
