test_that("create_gazepoint_pipeline_map creates the default workflow", {
  pipeline <- create_gazepoint_pipeline_map(pipeline_id = "demo_pipeline")

  expect_s3_class(pipeline, "gazepoint_pipeline_map")
  expect_named(pipeline, c("pipeline_id", "nodes", "edges", "summary", "parameters"))
  expect_equal(pipeline$pipeline_id, "demo_pipeline")
  expect_equal(nrow(pipeline$nodes), 10)
  expect_equal(nrow(pipeline$edges), 9)
  expect_equal(pipeline$summary$n_steps, 10)
  expect_equal(pipeline$summary$n_edges, 9)
  expect_equal(pipeline$summary$n_required_steps, 10)
  expect_equal(pipeline$summary$n_optional_steps, 0)

  expect_true(all(c(
    "step_id", "label", "domain", "description",
    "expected_order", "required", "status", "notes"
  ) %in% names(pipeline$nodes)))

  expect_true(all(c("from", "to", "edge_type", "description", "required") %in% names(pipeline$edges)))
  expect_equal(pipeline$nodes$step_id[1], "import")
  expect_equal(pipeline$nodes$step_id[nrow(pipeline$nodes)], "reporting")
})

test_that("create_gazepoint_pipeline_map supports custom steps and edges", {
  steps <- data.frame(
    step_id = c("import", "qc", "report"),
    label = c("Import", "QC", "Report"),
    domain = c("data_io", "qc", "reporting"),
    description = c("Read files", "Check quality", "Write report"),
    expected_order = c(1, 2, 3),
    required = c(TRUE, TRUE, FALSE),
    status = c("done", "planned", "planned"),
    notes = c("", "", "optional"),
    stringsAsFactors = FALSE
  )

  edges <- data.frame(
    from = c("import", "qc"),
    to = c("qc", "report"),
    edge_type = c("required", "optional"),
    stringsAsFactors = FALSE
  )

  pipeline <- create_gazepoint_pipeline_map(
    steps = steps,
    edges = edges,
    pipeline_id = "custom",
    include_default = FALSE
  )

  expect_s3_class(pipeline, "gazepoint_pipeline_map")
  expect_equal(nrow(pipeline$nodes), 3)
  expect_equal(nrow(pipeline$edges), 2)
  expect_equal(pipeline$summary$n_required_steps, 2)
  expect_equal(pipeline$summary$n_optional_steps, 1)
  expect_true(pipeline$parameters$custom_steps)
  expect_true(pipeline$parameters$custom_edges)
})

test_that("audit_gazepoint_pipeline_steps passes complete default pipelines", {
  pipeline <- create_gazepoint_pipeline_map()
  audit <- audit_gazepoint_pipeline_steps(pipeline)

  expect_s3_class(audit, "gazepoint_pipeline_audit")
  expect_named(audit, c("pipeline_id", "checks", "summary", "parameters"))
  expect_equal(audit$summary$n_steps, 10)
  expect_equal(audit$summary$n_edges, 9)
  expect_equal(audit$summary$n_fail, 0)
  expect_equal(audit$summary$n_warn, 0)
  expect_true(audit$summary$audit_pass)
  expect_true(any(audit$checks$check == "expected_steps" & audit$checks$status == "pass"))
  expect_true(any(audit$checks$check == "ordering" & audit$checks$status == "pass"))
})

test_that("audit_gazepoint_pipeline_steps reports missing, extra, and ordering issues", {
  steps <- data.frame(
    step_id = c("report", "import", "qc", "extra_step"),
    label = c("Report", "Import", "QC", "Extra"),
    expected_order = c(4, 1, 2, 3),
    required = TRUE,
    stringsAsFactors = FALSE
  )

  pipeline <- create_gazepoint_pipeline_map(steps = steps, include_default = FALSE)

  audit <- audit_gazepoint_pipeline_steps(
    pipeline,
    expected_steps = c("import", "qc", "analysis", "report"),
    required_order = c("import", "qc", "analysis", "report"),
    allow_extra = FALSE
  )

  expect_false(audit$summary$audit_pass)
  expect_true(audit$summary$n_fail >= 1)
  expect_true(audit$summary$n_warn >= 1)
  expect_true(any(audit$checks$check == "expected_steps" & audit$checks$item == "analysis" & audit$checks$status == "fail"))
  expect_true(any(audit$checks$check == "extra_steps" & audit$checks$item == "extra_step" & audit$checks$status == "warn"))
  expect_true(any(audit$checks$check == "ordering" & audit$checks$status == "warn"))
})

test_that("audit_gazepoint_pipeline_steps accepts steps data frames directly", {
  steps <- data.frame(
    step_id = c("import", "qc", "report"),
    label = c("Import", "QC", "Report"),
    stringsAsFactors = FALSE
  )

  audit <- audit_gazepoint_pipeline_steps(
    steps,
    expected_steps = c("import", "qc", "report"),
    required_order = c("import", "qc", "report")
  )

  expect_s3_class(audit, "gazepoint_pipeline_audit")
  expect_equal(audit$summary$n_fail, 0)
  expect_true(audit$summary$audit_pass)
})

test_that("export_gazepoint_pipeline_dot creates DOT text and optional files", {
  steps <- data.frame(
    step_id = c("1 import", "qc-step", "report"),
    label = c("Import \"raw\" files", "QC", "Report"),
    description = c("Read\\nfiles", "Check quality", "Write report"),
    expected_order = c(1, 2, 3),
    stringsAsFactors = FALSE
  )

  pipeline <- create_gazepoint_pipeline_map(steps = steps, include_default = FALSE)
  dot <- export_gazepoint_pipeline_dot(pipeline, include_descriptions = TRUE)

  expect_type(dot, "character")
  expect_length(dot, 1)
  expect_match(dot, "digraph gazepoint_pipeline", fixed = TRUE)
  expect_match(dot, "graph [rankdir=\"LR\"]", fixed = TRUE)
  expect_match(dot, "n_1_import", fixed = TRUE)
  expect_match(dot, "qc_step", fixed = TRUE)
  expect_match(dot, "Import \\\"raw\\\" files", fixed = TRUE)
  expect_match(dot, "Read\\\\nfiles", fixed = TRUE)

  outfile <- tempfile(fileext = ".dot")
  returned <- export_gazepoint_pipeline_dot(pipeline, file = outfile, graph_name = "my graph", rankdir = "TB")
  expect_true(file.exists(outfile))
  expect_equal(paste(readLines(outfile, warn = FALSE), collapse = "\n"), returned)
  expect_match(returned, "digraph my_graph", fixed = TRUE)
  expect_match(returned, "graph [rankdir=\"TB\"]", fixed = TRUE)
})

test_that("pipeline visualization helpers validate inputs", {
  expect_error(create_gazepoint_pipeline_map(include_default = NA), "include_default")
  expect_error(create_gazepoint_pipeline_map(steps = NULL, include_default = FALSE), "steps")
  expect_error(create_gazepoint_pipeline_map(steps = data.frame(label = "x"), include_default = FALSE), "step_id")
  expect_error(create_gazepoint_pipeline_map(steps = data.frame(step_id = c("a", "a")), include_default = FALSE), "unique")
  expect_error(create_gazepoint_pipeline_map(steps = data.frame(step_id = ""), include_default = FALSE), "non-empty")
  expect_error(create_gazepoint_pipeline_map(pipeline_id = c("a", "b")), "pipeline_id")

  steps <- data.frame(step_id = c("a", "b"), stringsAsFactors = FALSE)
  expect_error(create_gazepoint_pipeline_map(steps = steps, edges = data.frame(from = "a"), include_default = FALSE), "missing required")
  expect_error(create_gazepoint_pipeline_map(steps = steps, edges = data.frame(from = "a", to = "missing"), include_default = FALSE), "unknown")

  pipeline <- create_gazepoint_pipeline_map(steps = steps, include_default = FALSE)
  expect_error(audit_gazepoint_pipeline_steps(list()), "pipeline")
  expect_error(audit_gazepoint_pipeline_steps(pipeline, expected_steps = 1), "expected_steps")
  expect_error(audit_gazepoint_pipeline_steps(pipeline, allow_extra = NA), "allow_extra")

  expect_error(export_gazepoint_pipeline_dot(pipeline, graph_name = ""), "graph_name")
  expect_error(export_gazepoint_pipeline_dot(pipeline, rankdir = ""), "rankdir")
  expect_error(export_gazepoint_pipeline_dot(pipeline, include_descriptions = NA), "include_descriptions")
})
