from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response
from django.conf import settings
import os
import re
import datetime
import subprocess
import requests


class ComputeViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response({"message": "Success"})

    def create(self, request):
        data = request.data
        file_path = os.path.join(settings.STATICFILES_DIRS[0], 'terraform_templates/ec2.tf')

        instance_name = data.get('instance_name', 'custom-instance')
        with open(file_path, 'r') as f:
            file_data = f.read()
            updated_file_data = re.sub(r'variable "instance_name" \{[^}]*default\s*=\s*".*"', f'variable "instance_name" {{\n  description = "Name of the EC2 instance"\n  default     = "{instance_name}"', file_data)

        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        new_file_name = f'ec2_{timestamp}.tf'

        terraform_submodule_path = os.path.join(settings.BASE_DIR, 'terraform')
        new_file_path = os.path.join(terraform_submodule_path, new_file_name)

        with open(new_file_path, 'w') as tf_file:
            tf_file.write(updated_file_data)

        original_dir = os.getcwd()
        os.chdir(terraform_submodule_path)

        try:
            branch_name = f'feature/create-ec2-{timestamp}'
            subprocess.run(['git', 'checkout', '-b', branch_name], check=True)

            subprocess.run(['git', 'add', new_file_name], check=True)
            subprocess.run(['git', 'commit', '-m', 'Add updated Terraform configuration'], check=True)

            subprocess.run(['git', 'push', 'origin', branch_name], check=True)

            github_token = os.environ.get('GITHUB_TOKEN')
            if not github_token:
                return Response({"error": "GitHub token not provided"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            headers = {'Authorization': f'token {github_token}'}
            repo_owner = 'taha-junaid'
            repo_name = 'InfraPilot'
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
            else:
                return Response({"error": "Failed to create pull request", "details": response.json()}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except subprocess.CalledProcessError as e:
            return Response({"error": f"Git command failed: {e}"}, status=500)
        finally:
            subprocess.run(['git', 'checkout', 'main'], check=True)
            os.chdir(original_dir)

        return Response({"message": "Updated Terraform file pushed to new branch"})