output "id" {
  description = "The ID of the instance."
  value       = linode_instance.hidewall-node.id
}

output "ip_address" {
  value = linode_instance.hidewall-node.private_ip_address
  description = "The private IP address of the Linode instance"
}