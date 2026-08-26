test_that("create_gazepoint_audit_index normalizes audit objects and data frames", {
  pipeline <- create_gazepoint_pipeline_map(pipeline_id = "demo_pipeline")
  pipeline_audit <- audit_gazepoint_pipeline_steps(pipeline)

  manual_checks <- data.frame(
    check = c("metadata", "quality_control", "sidecars"),
    item = c("required_columns", "missingness", "json_sidecars"),
    status = c("pass", "warn", "fail"),
    message = c(
      "Required columns were present.",
      "Missingness requires review.",
      "One expected sidecar was missing."
    ),
    domain = c("metadata", "qc", "metadata"),
    stringsAsFactors = FALSE
  )

  summary_only <- list(
    summary = data.frame(
      n_files = 5,
      n_pass = 3,
      n_warn = 1,
      n_fail = 0,
      audit_pass = TRUE,
      stringsAsFactors = FALSE
    )
  )

  index <- create_gazepoint_audit_index(
    audits = list(
      pipeline = pipeline_audit,
      manual = manual_checks,
      inventory = summary_only
    )
  )

  expect_s3_class(index, "gazepoint_audit_index")
  expect_equal(nrow(index), 9)
  expect_true(all(c(
    "audit_id", "object_class", "source_table", "row_number",
    "check", "item", "status", "message", "path", "domain"
  ) %in% names(index)))

  expect_equal(sum(index$audit_id == "pipeline"), 5)
  expect_equal(sum(index$audit_id == "manual"), 3)
  expect_equal(sum(index$audit_id == "inventory"), 1)
  expect_true(any(index$status == "fail"))
  expect_true(any(index$status == "warn"))
  expect_true(any(index$status == "not_checked"))
  expect_true(any(index$source_table == "summary"))
})

test_that("create_gazepoint_audit_index handles empty and summary-row cases", {
  empty_index <- create_gazepoint_audit_index(NULL)
  expect_s3_class(empty_index, "gazepoint_audit_index")
  expect_equal(nrow(empty_index), 0)

  audit <- list(
    checks = data.frame(
      check = "metadata",
      item = "required_columns",
      status = "pass",
      stringsAsFactors = FALSE
    ),
    summary = data.frame(
      n_pass = 1,
      n_warn = 0,
      n_fail = 0,
      audit_pass = TRUE,
      stringsAsFactors = FALSE
    )
  )

  no_summary <- create_gazepoint_audit_index(audit)
  with_summary <- create_gazepoint_audit_index(audit, include_summary_rows = TRUE)

  expect_equal(nrow(no_summary), 1)
  expect_equal(nrow(with_summary), 2)
  expect_true("summary" %in% with_summary$source_table)

  unknown <- create_gazepoint_audit_index(list(custom = list(x = 1)))
  expect_equal(nrow(unknown), 1)
  expect_equal(unknown$status, "recorded")
  expect_equal(unknown$check, "object_record")
})

test_that("create_gazepoint_audit_index normalizes common status labels", {
  checks <- data.frame(
    check = paste0("check_", seq_len(9)),
    status = c("OK", "complete", "warning", "flagged", "missing", "error", "skip", "present", "unexpected"),
    stringsAsFactors = FALSE
  )

  index <- create_gazepoint_audit_index(checks)

  expect_equal(index$status[1], "pass")
  expect_equal(index$status[2], "pass")
  expect_equal(index$status[3], "warn")
  expect_equal(index$status[4], "warn")
  expect_equal(index$status[5], "fail")
  expect_equal(index$status[6], "fail")
  expect_equal(index$status[7], "not_checked")
  expect_equal(index$status[8], "recorded")
  expect_equal(index$status[9], "other")
})

test_that("summarize_gazepoint_audit_trail summarizes overall and grouped counts", {
  index <- create_gazepoint_audit_index(list(
    first = data.frame(
      check = c("a", "b", "c"),
      status = c("pass", "warn", "fail"),
      domain = c("metadata", "qc", "metadata"),
      stringsAsFactors = FALSE
    ),
    second = data.frame(
      check = c("d", "e"),
      status = c("not_checked", "recorded"),
      domain = c("qc", "reporting"),
      stringsAsFactors = FALSE
    )
  ))

  overall <- summarize_gazepoint_audit_trail(index)
  by_audit <- summarize_gazepoint_audit_trail(index, by = "audit_id")
  by_domain <- summarize_gazepoint_audit_trail(index, by = "domain")

  expect_s3_class(overall, "gazepoint_audit_trail_summary")
  expect_equal(overall$n_records, 5)
  expect_equal(overall$n_pass, 1)
  expect_equal(overall$n_warn, 1)
  expect_equal(overall$n_fail, 1)
  expect_equal(overall$n_not_checked, 1)
  expect_equal(overall$n_recorded, 1)
  expect_false(overall$audit_pass)
  expect_true(overall$needs_review)

  expect_equal(nrow(by_audit), 2)
  expect_true(all(c("first", "second") %in% by_audit$audit_id))
  expect_equal(by_audit$n_fail[by_audit$audit_id == "first"], 1)
  expect_equal(by_audit$n_fail[by_audit$audit_id == "second"], 0)

  expect_true("metadata" %in% by_domain$domain)
  expect_true("qc" %in% by_domain$domain)
  expect_equal(by_domain$n_records[by_domain$domain == "metadata"], 2)
})

test_that("summarize_gazepoint_audit_trail handles empty inputs", {
  index <- create_gazepoint_audit_index(NULL)
  summary <- summarize_gazepoint_audit_trail(index)
  grouped <- summarize_gazepoint_audit_trail(index, by = "audit_id")

  expect_s3_class(summary, "gazepoint_audit_trail_summary")
  expect_equal(nrow(summary), 0)
  expect_equal(nrow(grouped), 0)
  expect_true("audit_id" %in% names(grouped))
})

test_that("export_gazepoint_audit_trail_markdown creates plain Markdown and files", {
  index <- create_gazepoint_audit_index(data.frame(
    check = c("metadata", "qc", "sidecars"),
    item = c("columns", "missingness", "json"),
    status = c("pass", "warn", "fail"),
    message = c("Columns present", "Review missingness", "Missing sidecar"),
    stringsAsFactors = FALSE
  ))

  summary <- summarize_gazepoint_audit_trail(index, by = "audit_id")
  md <- export_gazepoint_audit_trail_markdown(
    index,
    summary = summary,
    title = "Demo audit trail",
    include_details = TRUE,
    max_details = 2
  )

  expect_type(md, "character")
  expect_length(md, 1)
  expect_match(md, "# Demo audit trail", fixed = TRUE)
  expect_match(md, "## Summary", fixed = TRUE)
  expect_match(md, "## Details", fixed = TRUE)
  expect_match(md, "_Detail table truncated to 2 rows._", fixed = TRUE)
  expect_match(md, "| audit_id |", fixed = TRUE)
  expect_match(md, "| metadata | columns | pass |", fixed = TRUE)

  outfile <- tempfile(fileext = ".md")
  returned <- export_gazepoint_audit_trail_markdown(index, file = outfile, include_details = FALSE)
  expect_true(file.exists(outfile))
  expect_equal(paste(readLines(outfile, warn = FALSE), collapse = "\n"), returned)
  expect_false(grepl("## Details", returned, fixed = TRUE))
})

test_that("audit trail helpers validate inputs", {
  expect_error(create_gazepoint_audit_index(1), "audits")
  expect_error(create_gazepoint_audit_index(data.frame(status = "pass"), audit_ids = c("a", "b")), "audit_ids")
  expect_error(create_gazepoint_audit_index(data.frame(status = "pass"), include_summary_rows = NA), "include_summary_rows")

  index <- create_gazepoint_audit_index(data.frame(check = "a", status = "pass"))
  expect_error(summarize_gazepoint_audit_trail(index, by = "missing_column"), "unknown column")
  expect_error(summarize_gazepoint_audit_trail(index, by = 1), "by")

  expect_error(export_gazepoint_audit_trail_markdown(index, summary = "bad"), "summary")
  expect_error(export_gazepoint_audit_trail_markdown(index, title = ""), "title")
  expect_error(export_gazepoint_audit_trail_markdown(index, include_details = NA), "include_details")
  expect_error(export_gazepoint_audit_trail_markdown(index, max_details = -1), "max_details")
})
