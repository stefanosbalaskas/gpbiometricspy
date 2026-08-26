#' Run blockwise online design optimization decision support
#'
#' Provides a safe, dependency-light decision-support/simulation helper for
#' online design optimization. The function recommends the next condition by
#' combining expected model-discrimination utility with optional exploration and
#' balancing penalties.
#'
#' This function does not control stimulus presentation software and should not
#' be used as autonomous real-time experiment control without separate ethical,
#' preregistration, and software-integration review.
#'
#' @param candidate_table A data frame containing candidate conditions.
#' @param condition_col Candidate condition column.
#' @param utility_col Expected utility/model-discrimination column.
#' @param block_col Optional block column.
#' @param cost_col Optional cost or burden column subtracted from utility.
#' @param previous_assignments Optional previous condition assignments.
#' @param exploration_weight Weight for favouring under-sampled conditions.
#' @param balance_weight Weight for penalising over-sampled conditions.
#' @param maximise Logical. If `TRUE`, select highest score.
#'
#' @return A list with `overview`, `ranked_candidates`, `recommendation`,
#'   `assignment_summary`, and `settings`.
#' @export
run_gazepoint_online_design_optimization <- function(candidate_table,
                                                     condition_col = "condition",
                                                     utility_col = "expected_utility",
                                                     block_col = NULL,
                                                     cost_col = NULL,
                                                     previous_assignments = NULL,
                                                     exploration_weight = 0.10,
                                                     balance_weight = 0.10,
                                                     maximise = TRUE) {
  if (!is.data.frame(candidate_table)) {
    stop("`candidate_table` must be a data frame.", call. = FALSE)
  }

  required <- c(condition_col, utility_col, block_col, cost_col)
  required <- required[!is.null(required)]

  missing_required <- setdiff(required, names(candidate_table))

  if (length(missing_required) > 0) {
    stop("Missing required columns: ", paste(missing_required, collapse = ", "), call. = FALSE)
  }

  if (!is.numeric(candidate_table[[utility_col]])) {
    stop("`utility_col` must identify a numeric column.", call. = FALSE)
  }

  if (!is.null(cost_col) && !is.numeric(candidate_table[[cost_col]])) {
    stop("`cost_col` must identify a numeric column.", call. = FALSE)
  }

  ranked <- candidate_table
  ranked$.condition <- as.character(ranked[[condition_col]])

  if (is.null(previous_assignments)) {
    previous_assignments <- character()
  } else if (is.data.frame(previous_assignments)) {
    if (!condition_col %in% names(previous_assignments)) {
      stop("`previous_assignments` data frame must contain `condition_col`.", call. = FALSE)
    }
    previous_assignments <- as.character(previous_assignments[[condition_col]])
  } else {
    previous_assignments <- as.character(previous_assignments)
  }

  condition_counts <- table(factor(
    previous_assignments,
    levels = unique(ranked$.condition)
  ))

  assignment_summary <- data.frame(
    condition = names(condition_counts),
    previous_n = as.integer(condition_counts),
    stringsAsFactors = FALSE
  )

  ranked$.previous_n <- assignment_summary$previous_n[
    match(ranked$.condition, assignment_summary$condition)
  ]

  ranked$.previous_n[is.na(ranked$.previous_n)] <- 0L

  max_previous <- max(ranked$.previous_n, 0)
  ranked$.exploration_bonus <- exploration_weight / (ranked$.previous_n + 1)
  ranked$.balance_penalty <- balance_weight * ifelse(
    max_previous > 0,
    ranked$.previous_n / max_previous,
    0
  )

  ranked$.cost <- if (!is.null(cost_col)) {
    ranked[[cost_col]]
  } else {
    0
  }

  ranked$.optimization_score <- ranked[[utility_col]] +
    ranked$.exploration_bonus -
    ranked$.balance_penalty -
    ranked$.cost

  ranked <- ranked[order(ranked$.optimization_score, decreasing = maximise), , drop = FALSE]
  ranked$optimization_rank <- seq_len(nrow(ranked))

  recommendation <- ranked[1, , drop = FALSE]

  overview <- data.frame(
    candidate_count = nrow(candidate_table),
    previous_assignment_count = length(previous_assignments),
    recommended_condition = recommendation$.condition[1],
    recommended_score = recommendation$.optimization_score[1],
    status = "online_design_recommendation_created",
    interpretation = paste(
      "The recommendation is blockwise design-optimization decision support.",
      "It does not autonomously control an experiment and does not prove which hypothesis is true."
    ),
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      ranked_candidates = ranked,
      recommendation = recommendation,
      assignment_summary = assignment_summary,
      settings = list(
        condition_col = condition_col,
        utility_col = utility_col,
        block_col = block_col,
        cost_col = cost_col,
        exploration_weight = exploration_weight,
        balance_weight = balance_weight,
        maximise = maximise
      )
    ),
    class = c("gazepoint_online_design_optimization", "list")
  )
}
