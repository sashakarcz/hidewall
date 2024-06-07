# File: modules/docker_swarm/main.tf

resource "null_resource" "docker_swarm" {
  connection {
    host        = var.host
    user        = var.user
    public_key  = var.public_key
  }

  provisioner "remote-exec" {
    inline = [
      "sudo apt update",
      "sudo apt install docker.io -y",
      "sudo systemctl start docker",
      "sudo systemctl enable docker",
      "sudo docker swarm init --listen-addr ${var.host}:2377"
    ]
  }
}
