package jarvis.approvals

default allow := false

# Example policy:
# - side_effects require approval unless actor has Jarvis.Admin
# - always allow read-only plans

allow {
  input.plan.side_effects == false
}

allow {
  input.plan.side_effects == true
  "Jarvis.Admin" in input.actor.roles
}

reason := "side_effects_require_approval" {
  input.plan.side_effects == true
  not ("Jarvis.Admin" in input.actor.roles)
}

reason := "allowed" {
  allow
}
