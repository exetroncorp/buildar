from dockerfile_parse import DockerfileParser
import subprocess
import uuid
import json

def pull_image(image_name):
    pull_command = ["udocker", "pull", image_name]
    if subprocess.run(pull_command).returncode != 0:
        print(f"Error: Failed to pull the image '{image_name}'")
        return None

def create_container(image_name):
    base_container_name = f"base_container_{uuid.uuid4()}"
    create_command = ["udocker", "--debug", "create", f"--name={base_container_name}", image_name]
    if subprocess.run(create_command).returncode != 0:
        print(f"Error: Failed to create the container from image '{image_name}'")
        return None
    return base_container_name

def execute_command(container_name, command):
    print(f"Executing: {command} in container {container_name}")
    run_command = ["udocker", "run", "--location=debinard/rootfs", "--name=" + container_name, "/bin/busybox", "sh", "-c", command]
    output_file = f"container_output_{container_name}.log"
    with open(output_file, 'w') as output:
        subprocess.run(run_command)
    print(f"Command execution completed. Output saved to {output_file}")

def apply_config(container_name, directive, args):
    image_path = f"debin:latest"
    config_command = ["umoci", "config", "--image", image_path]
    
    
    print("YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY")
    print(args)
    
    config_args = {
        "EXPOSE": ["--config.exposedports", args],
        "CMD": ["--config.cmd=" + arg for arg in json.loads(args)] if (directive == "CMD") else None ,
        "ENTRYPOINT": ["--config.entrypoint", args],
        "LABEL": ["--config.label", args],
        "ENV": ["--config.env", args],
        "USER": ["--config.user", args],
        "VOLUME": ["--config.volume", args],
        "WORKDIR": ["--config.workingdir", args],
        "STOPSIGNAL": ["--config.stopsignal", args],
    }

    if directive in config_args:
        
        print("YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY")
        print(args)
        print(config_args[directive])
        
        config_command.extend(config_args[directive])       
        result = subprocess.run(config_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print(result.stdout)
        print(result.stderr)

def run_oci_image_with_udocker(image_name):
    download_command = ["/workspaces/udocker/skopeo", "copy", "--insecure-policy", f"docker://{image_name}", "oci:debin:latest"]
    subprocess.run(download_command)
    unpack_command = ["umoci", "unpack", "--rootless", "--image", "debin:latest", "debinard"]
    subprocess.run(unpack_command)
    # Add any additional steps required to run the container

def process_dockerfile(dockerfile_path):
    parser = DockerfileParser()
    parser.content = open(dockerfile_path).read()

    current_container = None
    config_directives = []

    for instruction_dict in parser.structure:
        directive = instruction_dict["instruction"]
        args = instruction_dict["value"]

        if directive == "FROM":
            run_oci_image_with_udocker(args.strip())
            current_container = create_container(args)
        elif directive == "RUN":
            if current_container:
                execute_command(current_container, args)
        elif directive in ["EXPOSE", "CMD", "ENTRYPOINT", "LABEL", "ENV", "USER", "VOLUME", "WORKDIR", "STOPSIGNAL"]:
            if current_container:
                config_directives.append((directive, args))

    repack_command = ["umoci", "repack", "--image", "debin:latest", "debinard"]
    subprocess.run(repack_command)

    for directive, args in config_directives:
        if current_container:
            apply_config(current_container, directive, args)

    # Add any additional steps or cleanup as needed

if __name__ == "__main__":
    dockerfile_path = "Dockerfile"  # Replace with the path to your Dockerfile
    process_dockerfile(dockerfile_path)
