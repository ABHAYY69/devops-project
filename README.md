# 🚀 DevOps Project — Containerized App on AWS

![CI/CD](https://github.com/ABHAYY69/devops-project/actions/workflows/deploy.yml/badge.svg)

A production-grade DevOps project built by a 3rd year CS student demonstrating
real-world cloud infrastructure and automation.

## 🌍 Live Demo
http://52.66.196.7:5000

## 🛠️ Tech Stack
| Tool | Purpose |
|---|---|
| Python Flask | Web application |
| Docker | Containerization |
| AWS EC2 | Cloud hosting |
| AWS ECR | Docker image registry |
| Terraform | Infrastructure as Code |
| GitHub Actions | CI/CD Pipeline |

## 🏗️ Architecture
GitHub Push → GitHub Actions → Docker Build → Push to ECR → Deploy to EC2
## 🚀 How It Works
1. Developer pushes code to GitHub
2. GitHub Actions pipeline triggers automatically
3. Docker image is built and pushed to AWS ECR
4. EC2 instance pulls latest image and redeploys
5. App is live with zero manual intervention
## 📁 Project Structure
devops-project/
├── app.py                    # Flask application
├── Dockerfile                # Container configuration
├── requirements.txt          # Python dependencies
├── templates/
│   └── index.html           # Web UI
├── terraform/
│   └── main.tf              # AWS infrastructure code
└── .github/
└── workflows/
└── deploy.yml       # CI/CD pipeline

## ⚙️ Infrastructure (Terraform)
- **EC2 t3.micro** — App server
- **ECR Repository** — Docker image storage
- **Security Groups** — Network access control

## 🔄 CI/CD Pipeline
- Auto-triggered on every push to `main`
- Builds and pushes Docker image to ECR
- SSH deploys to EC2 automatically

## 👨‍💻 Author
**Abhay Patel** — 3rd Year CS Student
