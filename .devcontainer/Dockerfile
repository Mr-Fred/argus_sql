FROM mcr.microsoft.com/devcontainers/python:3.14-trixie

# Install system dependencies
# 1. Install prerequisites for adding repositories
RUN apt-get update && apt-get install -y curl gnupg lsb-release

# 2. Add Hashicorp (Terraform) Repository
RUN curl -fsSL https://apt.releases.hashicorp.com/gpg | gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/hashicorp.list

# 3. Add Google Cloud SDK Repository
RUN curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee /etc/apt/sources.list.d/google-cloud-sdk.list


# 4. Finally, update sources and install the CLI tools!
RUN apt-get update && apt-get install -y google-cloud-cli terraform


# Install UV
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"
