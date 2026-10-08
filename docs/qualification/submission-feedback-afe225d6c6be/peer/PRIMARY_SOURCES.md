# Primary API context for the independent review

Read 2026-10-08 from the official Instructure developer documentation.

- [Assignments: rubric criteria and assignment metadata](https://developerdocs.instructure.com/services/canvas/resources/assignments): criteria include an ID, ratings and potentially non-scoring metadata. Rubric settings and the flag linking a rubric to assignment grading are optional assignment fields. Preserve those meanings rather than infer a grade from criterion points.
- [Submissions: single-submission endpoint and returned metadata](https://developerdocs.instructure.com/services/canvas/resources/submissions): a single submission is retrieved by user ID, with explicit inclusion options for comments and rubric assessments. The current-attempt flag identifies resubmission since grading; a negative grader ID can represent automated grading. Neither a zero score nor a non-current grade should be converted into absent feedback.

Duplicate, missing, non-string and Unicode-variant criterion identifiers are deliberate defensive acceptance inputs. They are not a claim that Canvas routinely returns malformed identifiers. The review uses deterministic local response objects and errors; it does not establish live service availability or school-specific access.
