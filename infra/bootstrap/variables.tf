variable "subscription_id" {
  description = "Azure subscription to deploy into."
  type        = string
}

variable "location" {
  description = "Azure region for all resources (ADR 0003)."
  type        = string
  default     = "eastus2"
}

variable "prefix" {
  description = "Short prefix used in resource names."
  type        = string
  default     = "agentgw"
}

variable "alert_email" {
  description = "Email address that receives budget alerts."
  type        = string
}

variable "monthly_budget" {
  description = "Monthly subscription budget, in the billing currency."
  type        = number
  default     = 1000
}

variable "budget_start_date" {
  description = "First day of the month the budget starts (RFC3339). Must not be in the past when first created."
  type        = string
  default     = "2026-10-01T00:00:00Z"
}
