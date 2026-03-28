#!/usr/bin/env bash
set -euo pipefail

# ── Companion GCP Bootstrap Script ───────────────────────────────────────────
# Creates two GCP projects, enables APIs, creates Terraform state buckets,
# and sets up CI/CD service accounts.
#
# Prerequisites:
#   - gcloud CLI authenticated with an account that can create projects
#   - A GCP billing account ID
#
# Usage:
#   ./scripts/bootstrap-gcp.sh <billing-account-id> [org-id]
#
# Example:
#   ./scripts/bootstrap-gcp.sh 01ABCD-234EFG-567HIJ
#   ./scripts/bootstrap-gcp.sh 01ABCD-234EFG-567HIJ 123456789

BILLING_ACCOUNT="${1:?Usage: $0 <billing-account-id> [org-id]}"
ORG_ID="${2:-}"
REGION="us-central1"

STAGING_PROJECT="companion-staging"
PROD_PROJECT="companion-prod"

APIS=(
  run.googleapis.com
  sqladmin.googleapis.com
  redis.googleapis.com
  pubsub.googleapis.com
  storage.googleapis.com
  secretmanager.googleapis.com
  artifactregistry.googleapis.com
  documentai.googleapis.com
  texttospeech.googleapis.com
  speech.googleapis.com
  monitoring.googleapis.com
  cloudresourcemanager.googleapis.com
  vpcaccess.googleapis.com
  servicenetworking.googleapis.com
  compute.googleapis.com
  iam.googleapis.com
)

SA_ROLES=(
  roles/run.admin
  roles/cloudsql.admin
  roles/redis.admin
  roles/pubsub.admin
  roles/storage.admin
  roles/secretmanager.admin
  roles/artifactregistry.admin
  roles/monitoring.admin
  roles/compute.networkAdmin
  roles/vpcaccess.admin
  roles/iam.serviceAccountUser
  roles/serviceusage.serviceUsageAdmin
  roles/servicenetworking.networksAdmin
)

create_project() {
  local project_id="$1"

  echo "── Creating project: ${project_id}"

  if gcloud projects describe "$project_id" &>/dev/null; then
    echo "   Project ${project_id} already exists, skipping creation"
  else
    local org_flag=""
    if [[ -n "$ORG_ID" ]]; then
      org_flag="--organization=${ORG_ID}"
    fi
    gcloud projects create "$project_id" $org_flag
  fi

  echo "   Linking billing account"
  gcloud billing projects link "$project_id" --billing-account="$BILLING_ACCOUNT"

  echo "   Enabling APIs (this takes a minute)..."
  gcloud services enable "${APIS[@]}" --project="$project_id"

  echo "   ✓ Project ${project_id} ready"
}

create_terraform_state_bucket() {
  local project_id="$1"
  local bucket_name="${project_id}-tf-state"

  echo "── Creating Terraform state bucket: gs://${bucket_name}"

  if gcloud storage buckets describe "gs://${bucket_name}" --project="$project_id" &>/dev/null; then
    echo "   Bucket already exists, skipping"
  else
    gcloud storage buckets create "gs://${bucket_name}" \
      --project="$project_id" \
      --location="$REGION" \
      --uniform-bucket-level-access
  fi

  # Enable versioning for state recovery
  gcloud storage buckets update "gs://${bucket_name}" --versioning

  echo "   ✓ State bucket ready"
}

create_cicd_service_account() {
  local project_id="$1"
  local sa_name="companion-cicd"
  local sa_email="${sa_name}@${project_id}.iam.gserviceaccount.com"

  echo "── Creating CI/CD service account: ${sa_email}"

  if gcloud iam service-accounts describe "$sa_email" --project="$project_id" &>/dev/null; then
    echo "   Service account already exists, skipping creation"
  else
    gcloud iam service-accounts create "$sa_name" \
      --project="$project_id" \
      --display-name="Companion CI/CD"
  fi

  echo "   Granting IAM roles..."
  for role in "${SA_ROLES[@]}"; do
    gcloud projects add-iam-policy-binding "$project_id" \
      --member="serviceAccount:${sa_email}" \
      --role="$role" \
      --quiet
  done

  # Create and download key
  local key_file="/tmp/${project_id}-cicd-key.json"
  echo "   Creating service account key..."
  gcloud iam service-accounts keys create "$key_file" \
    --iam-account="$sa_email" \
    --project="$project_id"

  echo "   ✓ Service account ready"
  echo "   ⚠ Key saved to: ${key_file}"
  echo "   → Add this as GitHub secret GCP_SA_KEY for this environment"
}

# ── Main ─────────────────────────────────────────────────────────────────────

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║       Companion GCP Bootstrap                        ║"
echo "║       Staging: ${STAGING_PROJECT}                    ║"
echo "║       Prod:    ${PROD_PROJECT}                       ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Staging
create_project "$STAGING_PROJECT"
create_terraform_state_bucket "$STAGING_PROJECT"
create_cicd_service_account "$STAGING_PROJECT"

echo ""

# Prod
create_project "$PROD_PROJECT"
create_terraform_state_bucket "$PROD_PROJECT"
create_cicd_service_account "$PROD_PROJECT"

echo ""
echo "══════════════════════════════════════════════════════"
echo "Bootstrap complete."
echo ""
echo "Next steps:"
echo ""
echo "1. Add GitHub secrets (Settings → Secrets and variables → Actions):"
echo ""
echo "   For staging environment:"
echo "     GCP_SA_KEY       = contents of /tmp/${STAGING_PROJECT}-cicd-key.json"
echo "     GCP_PROJECT_ID   = ${STAGING_PROJECT}"
echo "     TF_STATE_BUCKET  = ${STAGING_PROJECT}-tf-state"
echo ""
echo "   For prod environment:"
echo "     GCP_SA_KEY       = contents of /tmp/${PROD_PROJECT}-cicd-key.json"
echo "     GCP_PROJECT_ID   = ${PROD_PROJECT}"
echo "     TF_STATE_BUCKET  = ${PROD_PROJECT}-tf-state"
echo ""
echo "2. Add GitHub variables (Settings → Variables):"
echo "     ENVIRONMENT      = staging (or prod)"
echo "     API_BASE_URL     = https://companion-staging-backend-xxxxx.run.app"
echo ""
echo "3. Deploy Terraform (staging first):"
echo "     cd infrastructure/terraform"
echo "     terraform init \\"
echo "       -backend-config=\"bucket=${STAGING_PROJECT}-tf-state\" \\"
echo "       -backend-config=\"prefix=staging\""
echo "     terraform plan \\"
echo "       -var-file=\"environments/staging.tfvars\" \\"
echo "       -var=\"project_id=${STAGING_PROJECT}\""
echo "     terraform apply"
echo ""
echo "4. Delete the key files after adding to GitHub:"
echo "     rm /tmp/${STAGING_PROJECT}-cicd-key.json"
echo "     rm /tmp/${PROD_PROJECT}-cicd-key.json"
echo "══════════════════════════════════════════════════════"
