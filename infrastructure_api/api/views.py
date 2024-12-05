from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response
from django.conf import settings
import os
import re
import datetime
import subprocess
import requests

def create_github_pr(new_file_path):

    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    original_dir = os.getcwd()
    os.chdir(os.path.dirname(new_file_path))

    branch_name = f'feature/create-ec2-{timestamp}'

    try:
        subprocess.run(['git', 'config', 'user.name', 'Api user'], check=True)
        subprocess.run(['git', 'config', 'user.email', 'infrapilot.dev@gmail.com'], check=True)

        repo_owner = 'taha-junaid'
        repo_name = 'InfraPilot'
        github_token = os.environ.get('GITHUB_TOKEN')

        if not github_token:
            return Response({"error": "GitHub token not provided"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        remote_url = f'https://{github_token}@github.com/{repo_owner}/{repo_name}.git'
        subprocess.run(['git', 'remote', 'set-url', 'origin', remote_url], check=True)

        subprocess.run(['git', 'checkout', 'main'], check=True)
        subprocess.run(['git', 'pull', 'origin', 'main'], check=True)

        subprocess.run(['git', 'checkout', '-b', branch_name], check=True)

        subprocess.run(['git', 'add', os.path.basename(new_file_path)], check=True)
        subprocess.run(['git', 'commit', '-m', 'Add updated Terraform configuration'], check=True)

        subprocess.run(['git', 'push', 'origin', branch_name], check=True)

        headers = {'Authorization': f'token {github_token}'}
        pr_title = f'Added EC2 configuration'
        pr_body = 'This PR was automatically created by the API to update the EC2 instance configuration.'
        pr_data = {
            'title': pr_title,
            'head': branch_name,
            'base': 'main',
            'body': pr_body
        }
        pr_url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/pulls'
        response = requests.post(pr_url, json=pr_data, headers=headers)

        if response.status_code == 201:
            pr_info = response.json()
            pr_url = pr_info.get('html_url')
            return Response({"message": "Pull request created successfully", "pull_request_url": pr_url}, status=status.HTTP_201_CREATED)
        else:
            return Response({"error": "Failed to create pull request", "details": response.json()}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except subprocess.CalledProcessError as e:
        if os.path.exists(new_file_path):
            os.remove(new_file_path)
        subprocess.run(['git', 'checkout', 'main'], check=True)
        subprocess.run(['git', 'branch', '-D', branch_name], check=True)
        return Response({"error": f"Git command failed: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    finally:
        subprocess.run(['git', 'checkout', 'main'], check=True)
        os.chdir(original_dir)


class ComputeViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response({"message": "Success"})

    def create(self, request):
        data = request.data
        file_path = os.path.join(settings.STATICFILES_DIRS[0], 'terraform_templates/ec2.tf')
        instance_name = data.get('instance_name', 'custom-instance')

        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        new_file_name = f'ec2_{timestamp}.tf'

        terraform_submodule_path = os.path.join(settings.BASE_DIR, 'terraform')
        new_file_path = os.path.join(terraform_submodule_path, new_file_name)

        with open(file_path, 'r') as f:
            file_data = f.read()
            updated_file_data = re.sub(
                r'variable "instance_name" \{[^}]*default\s*=\s*".*"',
                f'variable "instance_name" {{\n  description = "Name of the EC2 instance"\n  default     = "{instance_name}"',
                file_data
            )

        with open(new_file_path, 'w') as tf_file:
            tf_file.write(updated_file_data)

        return create_github_pr(new_file_path)