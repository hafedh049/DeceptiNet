import os
import json
import subprocess
import paramiko
from dotenv import load_dotenv, dotenv_values
import time
import re
from pathlib import Path

# -------------------
# Load environment
# -------------------
load_dotenv()

BASE_VM_DIR = os.getenv("BASE_VM_DIR")
BASE_VM_PATH = os.getenv("BASE_VM_PATH")
BASE_VM_USERNAME = os.getenv("BASE_VM_USERNAME")
BASE_VM_PASSWORD = os.getenv("BASE_VM_PASSWORD")

# -------------------
# Utility functions
# -------------------
def load_vms():
    with open("vms.json", "r", encoding="utf-8", errors="ignore") as f:
        return json.load(f)


def save_vms(vms):
    with open("vms.json", "w", encoding="utf-8", errors="ignore") as f:
        json.dump(vms, f, indent=4)


def create_vm(vm):
    name = vm["name"]
    path, ip = vm.get("path"), vm.get("ip")

    if path and ip and os.path.exists(path):
        return vm

    vm_path = os.path.join(BASE_VM_DIR, name, f"{name}.vmx")
    clone_cmd = ["vmrun", "clone", BASE_VM_PATH, vm_path, "full", f"--cloneName={name}"]

    print(f"[+] Cloning VM {name}...")
    subprocess.run(clone_cmd, check=True)

    print(f"[+] Starting VM {name}...")
    subprocess.run(["vmrun", "start", vm_path, "gui"], check=True)

    print(f"[~] Waiting for VM {name} to get IP...")
    while True:
        time.sleep(1)
        try:
            ip = (
                subprocess.check_output(
                    ["vmrun", "getGuestIPAddress", vm_path, "-wait"]
                )
                .decode()
                .strip()
            )
            if ip:
                break
        except subprocess.CalledProcessError:
            continue

    vm["path"] = vm_path.replace("\\", "/")
    vm["ip"] = ip
    print(f"[✓] VM {name} ready at {ip}")
    return vm


def boot_vm(vm):
    path = vm.get("path")
    if path:
        print(f"[+] Booting VM {vm['name']}...")
        subprocess.run(["vmrun", "start", path, "gui"], check=True)


def ssh_connect(ip, port=22):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, username=BASE_VM_USERNAME, password=BASE_VM_PASSWORD, port=port)
    return ssh


def copy_files(ssh, local_dir, remote_base_dir, vms=None):
    sftp = ssh.open_sftp()

    def upload_dir(local_path, remote_path):
        try:
            sftp.mkdir(remote_path)
        except IOError:
            pass
        for item in Path(local_path).iterdir():
            remote_item = f"{remote_path}/{item.name}"
            if item.is_dir():
                upload_dir(item, remote_item)
            elif item.is_file():
                with open(item, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                    # Replace VM IP placeholders
                    if vms:
                        for vm in vms:
                            placeholder_key = f"{vm['name']}_IP"
                            content = re.sub(
                                r"\{\s*\{\s*" + re.escape(placeholder_key) + r"\s*\}\s*\}",
                                vm["ip"],
                                content,
                            )

                    # Replace .env variables
                    for key, value in dotenv_values(".env").items():
                        content = re.sub(
                            r"\{\s*\{\s*" + re.escape(key) + r"\s*\}\s*\}",
                            value,
                            content,
                        )

                with sftp.file(remote_item, "w") as remote_file:
                    remote_file.write(content)
                sftp.chmod(remote_item, 0o644)

    upload_dir(local_dir, remote_base_dir)
    sftp.close()


# -------------------
# Main execution
# -------------------
if __name__ == "__main__":
    vms = load_vms()

    # 1. Create/ensure VMs ready
    for idx, vm in enumerate(vms):
        vms[idx] = create_vm(vm)
    save_vms(vms)

    # 2. Boot all VMs marked 'start'
    for vm in [v for v in vms if v.get("state", "stop") == "start"]:
        boot_vm(vm)

    # 3. Configure Ansible Master
    Ansible_ip = next((vm["ip"] for vm in vms if vm["name"] == "Ansible"), None)
    if not Ansible_ip:
        print("[x] Ansible Master has no IP")
        exit(1)

    ssh = ssh_connect(Ansible_ip)

    commands = [
        f"subscription-manager register --force --username '{os.getenv('REDHAT_USERNAME')}' --password '{os.getenv('REDHAT_PASSWORD')}'",
        "dnf install -y ansible-core python3-pip sshpass tree jq nmap",
        "ansible-galaxy collection install ansible.posix community.general",
        "echo '[defaults]' | tee /root/ansible.cfg",
        "echo 'forks = 20' | tee -a /root/ansible.cfg",
        "echo 'inventory = /root/inventory' | tee -a /root/ansible.cfg",
        "echo 'deprecation_warnings = False' | tee -a /root/ansible.cfg",
        "echo '[all]' | tee /root/inventory",
    ]

    target_vms = [vm for vm in vms if vm["name"] != "Ansible" and vm.get("state") == "start"]
    for vm in target_vms:
        safe_name = vm["name"].replace(" ", "-")
        port = int(os.getenv("T_POT_PORT")) if vm["name"] == "T-Pot" else 22
        commands.append(
            f"grep -q '{safe_name} ansible_host={vm['ip']}' /root/inventory || echo '{safe_name} ansible_host={vm['ip']} python_interpreter=/usr/bin/python3 ansible_port={port}' | tee -a /root/inventory"

        )
        commands.append(
            f"grep -q '{vm['ip']} {safe_name}' /etc/hosts || echo '{vm['ip']} {safe_name}' | tee -a /etc/hosts"
        )

    for cmd in commands:
        stdin, stdout, stderr = ssh.exec_command(cmd)
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            print(f"[✓] {cmd}")
        else:
            print(f"[x] Failed: {cmd}\n{stderr.read().decode()}")
            exit(1)

    # SSH key setup
    ssh.exec_command("rm -rf /root/.ssh && mkdir -p /root/.ssh && chmod 700 /root/.ssh")
    ssh.exec_command("ssh-keygen -t rsa -b 2048 -f /root/.ssh/id_rsa -q -N '' <<< y")
    ssh.exec_command("chmod 600 /root/.ssh/id_rsa /root/.ssh/id_rsa.pub")

    for vm in target_vms:
        port = int(os.getenv("T_POT_PORT")) if vm["name"] == "T-Pot" else 22
        cmd = f"sshpass -p '{BASE_VM_PASSWORD}' ssh-copy-id -f -o StrictHostKeyChecking=no -p {port} {BASE_VM_USERNAME}@{vm['ip']}"
        time.sleep(2)
        stdin, stdout, stderr = ssh.exec_command(cmd)
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            print(f"[✓] Key copied to {vm['name']}")
        else:
            print(f"[x] Failed to copy key to {vm['name']}")
            exit(1)

    # 4. Copy folders
    for folder in ["playbooks", "scripts", "manifests", "web-application"]:
        copy_files(ssh, folder, f"/root/{folder}", vms=target_vms)

    ssh.close()
    print("[✓] All VM setup tasks completed.")
