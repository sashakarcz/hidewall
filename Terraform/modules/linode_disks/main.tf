# modules/linode_instance_disk/main.tf
resource "linode_instance_disk" "disk" {
  linode_id   = var.linode_id
  label       = var.label
  size        = var.size
  image       = var.image
}

output "linode_disk_id" {
  value = linode_instance_disk.disk.id
}
