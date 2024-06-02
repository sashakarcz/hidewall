resource "linode_firewall" "ingress" {
  label           = "ingress"
  linodes         = var.linodes
  inbound_policy  = "DROP"
  outbound_policy = "ACCEPT"

  inbound {
    action   = "DROP"
    protocol = "TCP"
    ports    = "22"
    ipv4     = ["0.0.0.0/0"]
    ipv6     = ["::/0"]
    label    = "drop-inbound-SSH"
  }

  inbound {
    action   = "ACCEPT"
    protocol = "TCP"
    ports    = "2377"
    ipv4     = ["10.69.0.0/24"]
    label    = "local-docker-swarm"
  }

  inbound {
    action   = "ACCEPT"
    protocol = "TCP"
    ports    = "1-65535"
    ipv4     = ["192.168.255.0/24", "10.69.0.0/24", "192.168.128.0/17"]
    label    = "accept-inbound-tcp"
  }

  inbound {
    action   = "ACCEPT"
    protocol = "UDP"
    ports    = "1-65535"
    ipv4     = ["192.168.255.0/24", "10.69.0.0/24", "192.168.128.0/17"]
    label    = "accept-inbound-udp"
  }

  inbound {
    action   = "ACCEPT"
    protocol = "ICMP"
    ipv4     = ["192.168.255.0/24", "10.69.0.0/24", "192.168.128.0/17"]
    label    = "accept-inbound-icmp"
  }

  inbound {
    action   = "ACCEPT"
    protocol = "IPENCAP"
    ipv4     = ["192.168.255.0/24", "10.69.0.0/24", "192.168.128.0/17"]
    label    = "accept-inbound-ipencap"
  }

  inbound {
    action   = "ACCEPT"
    protocol = "TCP"
    ports    = "1-65535"
    ipv4     = ["198.41.192.77/32"]
    label    = "accept-cf-tunnel"
  }
}