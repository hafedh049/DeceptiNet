#!/bin/bash
# Interactive script to run or delete Ansible playbooks

PLAYBOOK_DIR="./playbooks"

# Explicit installation and deletion lists
INSTALLATION_PLAYBOOKS=(
    "hostnames-installation.yaml"
    "subscription-manager-installation.yaml"
    "k3s-installation.yaml"
    "application-installation.yaml"
    "caldera-installation.yaml"
    "grafana-loki-installation.yaml"
    "n8n-installation.yaml"
    "promtail-installation.yaml"
    "hashicorp-installation.yaml"
)

DELETION_PLAYBOOKS=(
    "application-deletion.yaml"
    "caldera-deletion.yaml"
    "grafana-loki-deletion.yaml"
    "k3s-deletion.yaml"
    "n8n-deletion.yaml"
    "promtail-deletion.yaml"
    "hashicorp-deletion.yaml"
)

echo "Select operation:"
echo "1) Full Installation"
echo "2) Full Purge/Deletion"
echo "3) Run specific installation playbooks"
echo "4) Run specific deletion playbooks"
echo "5) Delete specific playbooks from disk"
read -rp "Enter choice (1-5): " CHOICE

TO_RUN=()
TO_DELETE=()

case "$CHOICE" in
1)
    # Full Installation
    TO_RUN=("${INSTALLATION_PLAYBOOKS[@]}")
    ;;
2)
    # Full Purge/Deletion
    TO_RUN=("${DELETION_PLAYBOOKS[@]}")
    ;;
3)
    # Run specific installation playbooks
    echo "Available installation playbooks:"
    for i in "${!INSTALLATION_PLAYBOOKS[@]}"; do
        printf "%2d) %s\n" "$i" "${INSTALLATION_PLAYBOOKS[$i]}"
    done
    read -rp "Enter playbook numbers to run (space separated): " SELECTED
    for n in $SELECTED; do
        [[ $n -ge 0 && $n -lt ${#INSTALLATION_PLAYBOOKS[@]} ]] && TO_RUN+=("${INSTALLATION_PLAYBOOKS[$n]}")
    done
    ;;
4)
    # Run specific deletion playbooks
    echo "Available deletion playbooks:"
    for i in "${!DELETION_PLAYBOOKS[@]}"; do
        printf "%2d) %s\n" "$i" "${DELETION_PLAYBOOKS[$i]}"
    done
    read -rp "Enter playbook numbers to run (space separated): " SELECTED
    for n in $SELECTED; do
        [[ $n -ge 0 && $n -lt ${#DELETION_PLAYBOOKS[@]} ]] && TO_RUN+=("${DELETION_PLAYBOOKS[$n]}")
    done
    ;;
5)
    # Delete any playbooks from disk
    echo "Available playbooks in $PLAYBOOK_DIR:"
    ls -1 "$PLAYBOOK_DIR"
    read -rp "Enter playbook names to delete (space separated): " SELECTED
    TO_DELETE=($SELECTED)
    ;;
*)
    echo "Invalid choice. Exiting."
    exit 1
    ;;
esac

# Run selected playbooks
for pb in "${TO_RUN[@]}"; do
    FILE="$PLAYBOOK_DIR/$pb"
    if [[ -f "$FILE" ]]; then
        echo -e "\n==== Running playbook: $pb ===="
        ansible-playbook "$FILE"
        if [[ $? -ne 0 ]]; then
            echo "Error: Playbook $pb failed. Exiting."
            exit 1
        fi
    else
        echo "Warning: Playbook $pb not found in $PLAYBOOK_DIR. Skipping."
    fi
done

# Delete selected playbooks
for pb in "${TO_DELETE[@]}"; do
    FILE="$PLAYBOOK_DIR/$pb"
    if [[ -f "$FILE" ]]; then
        echo -e "\n==== Deleting playbook: $pb ===="
        rm -f "$FILE"
        echo "Deleted $pb"
    else
        echo "Warning: Playbook $pb not found in $PLAYBOOK_DIR. Skipping."
    fi
done

echo -e "\nOperation completed successfully!"