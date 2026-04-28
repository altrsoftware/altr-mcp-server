ALTR MCP server for managing data security on Snowflake. Provides tools for tag management, masking policy and rule CRUD, automated data classification, role discovery, access management, audits, telemetry, and sidecar configuration.

IMPORTANT: Classification jobs (create_job) are async and can take 10-30+ minutes. After creating a job, stop and tell the user to wait for completion. Poll with get_jobs until status is COMPLETED before calling get_classification_report.

MASKING LEVELS (use these exact values with add_rules):
10000 = No Mask, 10001 = Full Mask, 10002 = Email Mask, 10003 = Show Last Four, 10004 = Constant Mask, 10005 = Null, 10006 = Full Mask Hash, 10007 = Email Hash, 10008 = Show Last Four Hash, 10009 = Constant Date. There are exactly 10 masking levels (10000-10009). Do NOT claim any level is invalid or unsupported.

TOOL USAGE GUIDANCE

These tools cover four areas of ALTR data security:

  Discovery     — get_databases, get_database_id,
                  get_roles, get_tags, get_tag_values,
                  get_policies, get_rules
  Classification — get_classifiers, create_classifier,
                   delete_classifier, get_collections,
                   create_collection, delete_collection,
                   create_job, get_jobs,
                   update_job_status,
                   get_classification_report
  Tagging        — connect_tag,
                   update_tag, delete_tag,
                   delete_tag_by_details,
                   get_tag_details,
                   get_tag_details_by_group_id
  Policy/Rules   — create_policy, add_rules,
                   update_rule, delete_policy,
                   delete_rule
  Access Mgmt    — create_snowflake_access_policy,
                   create_oltp_access_policy,
                   update_snowflake_access_policy,
                   trigger_access_policy_check
  Access Request — create_access_request,
                   get_access_requests,
                   get_access_request,
                   approve_access_request,
                   deny_access_request,
                   cancel_access_request
  Telemetry      — get_agent_instances,
                   get_agent_instance,
                   delete_agent_instance,
                   get_agent_task_telemetry,
                   get_sidecar_instances,
                   get_sidecar_instance,
                   delete_sidecar_instance,
                   get_task_telemetry,
                   delete_task_telemetry
  Audits         — search_audits, get_audit_results
  Sidecar Config — list_sc_agents, create_sc_agent, get_sc_agent,
                   update_sc_agent, delete_sc_agent,
                   list_sc_repos, create_sc_repo, get_sc_repo,
                   update_sc_repo, delete_sc_repo,
                   list_sc_repo_users, create_sc_repo_user, get_sc_repo_user,
                   update_sc_repo_user, delete_sc_repo_user,
                   list_sc_service_users, create_sc_service_user,
                   get_sc_service_user, update_sc_service_user,
                   delete_sc_service_user,
                   list_sc_sidecars, create_sc_sidecar, get_sc_sidecar,
                   update_sc_sidecar, delete_sc_sidecar,
                   list_sc_sidecar_listeners, register_sc_sidecar_listener,
                   deregister_sc_sidecar_listener,
                   list_sc_sidecar_bindings, list_sc_repo_bindings,
                   get_sc_sidecar_binding, create_sc_sidecar_binding,
                   delete_sc_sidecar_binding

Common workflow (end-to-end setup):

  1. Discover existing state — databases, tags, policies, roles
  2. Run a classification job to find sensitive columns
     IMPORTANT: Classification jobs are async and can take 10-30+ minutes.
     After creating a job, STOP and tell the user to wait for it to finish.
     Do NOT proceed until get_jobs shows status COMPLETED.
  3. Review the classification report (get_classification_report)
  4. Check if the needed Snowflake tags already exist using get_tags.
     This server connects existing Snowflake tags to ALTR — it does not
     create tags in Snowflake. If tags are missing, instruct the user to
     create them in Snowflake first (via the Snowflake console, SQL, or
     another MCP server like snowflake-labs-mcp).
  5. Connect Snowflake tags to ALTR (connect_tag)
  6. Create masking policies (create_policy) and add rules (add_rules)

These steps are not always required in order — users may skip classification
if they already know which columns to tag, or they may only need to add rules
to an existing policy. Adapt to what the user asks for.
