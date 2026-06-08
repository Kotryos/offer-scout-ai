data "google_project" "current" {
  project_id = var.project_id
}

locals {
  github_deployer_member = "serviceAccount:github-deployer@${var.project_id}.iam.gserviceaccount.com"

  secret_ids = toset([
    "gmail-smtp-credentials",
    "groq-api-key",
    "jina-api-key",
    "profile-context",
    "resend-credentials",
    "tavily-api-key",
  ])

  agent_secret_ids = toset(concat(
    ["groq-api-key", "tavily-api-key"],
    var.enable_jina_api_key ? ["jina-api-key"] : [],
  ))

  coordinator_secret_ids = toset([
    "gmail-smtp-credentials",
    "profile-context",
    "resend-credentials",
  ])
}

resource "google_service_account" "agent_runtime" {
  project      = var.project_id
  account_id   = "scout-agent-runtime"
  display_name = "Scout Agent runtime"
}

resource "google_service_account" "coordinator_runtime" {
  project      = var.project_id
  account_id   = "scout-coordinator-runtime"
  display_name = "Scout Coordinator runtime"
}

resource "google_service_account" "tasks_invoker" {
  project      = var.project_id
  account_id   = "scout-tasks-invoker"
  display_name = "Scout Coordinator Cloud Tasks invoker"
}

resource "google_secret_manager_secret" "secrets" {
  for_each = local.secret_ids

  project   = var.project_id
  secret_id = each.value

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_iam_member" "agent_secret_access" {
  for_each = local.agent_secret_ids

  project   = var.project_id
  secret_id = google_secret_manager_secret.secrets[each.value].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.agent_runtime.email}"
}

resource "google_secret_manager_secret_iam_member" "coordinator_secret_access" {
  for_each = local.coordinator_secret_ids

  project   = var.project_id
  secret_id = google_secret_manager_secret.secrets[each.value].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.coordinator_runtime.email}"
}

resource "google_project_iam_member" "coordinator_cloud_tasks_enqueuer" {
  project = var.project_id
  role    = "roles/cloudtasks.enqueuer"
  member  = "serviceAccount:${google_service_account.coordinator_runtime.email}"
}

resource "google_cloud_tasks_queue" "email_processing" {
  project  = var.project_id
  name     = var.tasks_queue_name
  location = var.region

  rate_limits {
    max_dispatches_per_second = 1
    max_concurrent_dispatches = 1
  }

  retry_config {
    max_attempts       = 3
    min_backoff        = "10s"
    max_backoff        = "300s"
    max_doublings      = 3
    max_retry_duration = "1800s"
  }

  stackdriver_logging_config {
    sampling_ratio = 1.0
  }
}

resource "google_service_account_iam_member" "coordinator_can_use_tasks_invoker" {
  service_account_id = google_service_account.tasks_invoker.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.coordinator_runtime.email}"
}

resource "google_service_account_iam_member" "cloud_tasks_can_mint_oidc" {
  service_account_id = google_service_account.tasks_invoker.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-cloudtasks.iam.gserviceaccount.com"
}

resource "google_service_account_iam_member" "github_can_use_agent_runtime" {
  service_account_id = google_service_account.agent_runtime.name
  role               = "roles/iam.serviceAccountUser"
  member             = local.github_deployer_member
}

resource "google_service_account_iam_member" "github_can_use_coordinator_runtime" {
  service_account_id = google_service_account.coordinator_runtime.name
  role               = "roles/iam.serviceAccountUser"
  member             = local.github_deployer_member
}

resource "google_cloud_run_v2_service" "agent" {
  count = var.deploy_services ? 1 : 0

  project             = var.project_id
  name                = var.agent_service_name
  location            = var.region
  deletion_protection = false
  ingress             = "INGRESS_TRAFFIC_ALL"

  scaling {
    max_instance_count = var.max_instance_count
  }

  template {
    service_account = google_service_account.agent_runtime.email
    timeout         = "300s"

    containers {
      image = var.agent_image

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
      }

      env {
        name = "GROQ_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.secrets["groq-api-key"].secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "TAVILY_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.secrets["tavily-api-key"].secret_id
            version = "latest"
          }
        }
      }

      dynamic "env" {
        for_each = var.enable_jina_api_key ? [1] : []

        content {
          name = "JINA_API_KEY"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.secrets["jina-api-key"].secret_id
              version = "latest"
            }
          }
        }
      }
    }
  }

  depends_on = [
    google_secret_manager_secret_iam_member.agent_secret_access,
  ]
}

resource "google_cloud_run_v2_service" "coordinator" {
  count = var.deploy_services ? 1 : 0

  project             = var.project_id
  name                = var.coordinator_service_name
  location            = var.region
  deletion_protection = false
  ingress             = "INGRESS_TRAFFIC_ALL"

  scaling {
    max_instance_count = var.max_instance_count
  }

  template {
    service_account = google_service_account.coordinator_runtime.email
    timeout         = "300s"

    containers {
      image = var.coordinator_image

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      env {
        name  = "TASK_BACKEND"
        value = "cloud_tasks"
      }

      env {
        name  = "CLOUD_TASKS_PROJECT"
        value = var.project_id
      }

      env {
        name  = "CLOUD_TASKS_LOCATION"
        value = var.region
      }

      env {
        name  = "CLOUD_TASKS_QUEUE"
        value = google_cloud_tasks_queue.email_processing.name
      }

      env {
        name  = "CLOUD_TASKS_SERVICE_ACCOUNT_EMAIL"
        value = google_service_account.tasks_invoker.email
      }

      env {
        name  = "SCOUT_AGENT_BASE_URL"
        value = google_cloud_run_v2_service.agent[0].uri
      }

      env {
        name  = "SCOUT_AGENT_AUDIENCE"
        value = google_cloud_run_v2_service.agent[0].uri
      }

      env {
        name  = "SCOUT_AGENT_AUTH_MODE"
        value = "cloud_run_oidc"
      }

      env {
        name  = "RESEND_BASE_URL"
        value = "https://api.resend.com"
      }

      env {
        name  = "GMAIL_SMTP_HOST"
        value = "smtp.gmail.com"
      }

      env {
        name  = "GMAIL_SMTP_PORT"
        value = "587"
      }

      env {
        name = "RESEND_CREDENTIALS"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.secrets["resend-credentials"].secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "GMAIL_SMTP_CREDENTIALS"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.secrets["gmail-smtp-credentials"].secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "PROFILE_CONTEXT"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.secrets["profile-context"].secret_id
            version = "latest"
          }
        }
      }
    }
  }

  depends_on = [
    google_project_iam_member.coordinator_cloud_tasks_enqueuer,
    google_secret_manager_secret_iam_member.coordinator_secret_access,
    google_service_account_iam_member.coordinator_can_use_tasks_invoker,
    google_service_account_iam_member.cloud_tasks_can_mint_oidc,
  ]
}

resource "google_cloud_run_v2_service_iam_member" "coordinator_public_invoker" {
  count = var.deploy_services ? 1 : 0

  project  = var.project_id
  location = google_cloud_run_v2_service.coordinator[0].location
  name     = google_cloud_run_v2_service.coordinator[0].name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service_iam_member" "coordinator_invokes_agent" {
  count = var.deploy_services ? 1 : 0

  project  = var.project_id
  location = google_cloud_run_v2_service.agent[0].location
  name     = google_cloud_run_v2_service.agent[0].name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.coordinator_runtime.email}"
}
