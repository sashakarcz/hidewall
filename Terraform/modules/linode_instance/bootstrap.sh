#!/bin/bash

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Clone the repository
git clone https://github.com/sashakarcz/hidewall.git

# Change directory to the cloned repository
cd hidewall

# Perform any additional setup or configuration here

# Run any necessary commands or scripts
# Initialize Docker Swarm on the current node
docker swarm init

# Retrieve the join token for worker nodes
JOIN_TOKEN=$(docker swarm join-token -q worker)

# Loop through each node and join them to the Swarm cluster
for node in $(docker node ls --format "{{.Hostname}}"); do
    # Skip the current node (manager node)
    if [[ $node != $(hostname) ]]; then
        # Join the node to the Swarm cluster
        ssh $node "docker swarm join --token $JOIN_TOKEN $(hostname):2377"
    fi
done
# Exit the script
exit 0