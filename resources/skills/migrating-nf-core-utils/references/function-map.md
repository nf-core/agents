# Vendored helpers to plugin calls

Examples target nf-core-utils 0.7.0 and nf-schema 2.7.2. Verify exports and overloads against the versions being pinned before applying them. Include each function from `plugin/nf-core-utils` or `plugin/nf-schema` in the Nextflow file that calls it.

## UTILS_NEXTFLOW_PIPELINE

Replace the version, parameter-dump and Conda checks with the corresponding plugin calls, preserving the original conditions:

```groovy
include { getWorkflowVersion; dumpParametersToJSON; checkCondaChannels } from 'plugin/nf-core-utils'

if (version) {
    log.info("${workflow.manifest.name} ${getWorkflowVersion(workflow.manifest.version, workflow.commitId)}")
    System.exit(0)
}
if (outdir) {
    dumpParametersToJSON(outdir, params)
}
if (workflow.profile.tokenize(',').intersect(['conda', 'mamba']).size() >= 1) {
    checkCondaChannels()
}
```

## UTILS_NFSCHEMA_PLUGIN

Use the pipeline's existing help variables and text. This example assumes their names match the vendored workflow inputs:

```groovy
include { paramsHelp; paramsSummaryLog; validateParameters } from 'plugin/nf-schema'

if (help || help_full) {
    log.info(paramsHelp(
        [
            beforeText: before_text,
            afterText: after_text,
            command: command,
            showHidden: show_hidden,
            fullHelp: help_full,
        ],
        (help instanceof String && help != 'true') ? help : '',
    ))
    System.exit(0)
}
log.info(before_text)
log.info(paramsSummaryLog(workflow, parameters_schema: 'nextflow_schema.json'))
log.info(after_text)
if (validate_params) {
    validateParameters(parameters_schema: 'nextflow_schema.json')
}
```

Copy any additional validation options from the original call. Other nf-schema imports, such as `samplesheetToList` and `paramsSummaryMap`, remain direct plugin calls.

nf-schema 2.7.2 accepts `paramsSummaryLog(Map, WorkflowMetadata)` and `paramsSummaryLog(WorkflowMetadata)`, with the same shapes for `paramsSummaryMap`. nf-schema 3.x removes the `WorkflowMetadata` argument; use its version-specific API instead of copying this example unchanged.

## UTILS_NFCORE_PIPELINE

Replace startup checks with:

```groovy
include { checkConfigProvided; checkProfileProvided } from 'plugin/nf-core-utils'

checkConfigProvided()
checkProfileProvided(nextflow_cli_args)
```

`checkProfileProvided` also accepts a second boolean argument for monochrome logs. Completion hooks retain these call shapes; change their imports to `plugin/nf-core-utils` without moving them out of their existing lifecycle hooks:

```groovy
completionEmail(summary_params, email, email_on_fail, plaintext_email, outdir, monochrome_logs, multiqc_reports)
completionSummary(monochrome_logs)
imNotification(summary_params, hook_url)
```

## Local helpers

| Local helper                               | Plugin replacement                                                                                  |
| ------------------------------------------ | --------------------------------------------------------------------------------------------------- |
| `getGenomeAttribute(attribute)`            | `getGenomeAttribute(attribute)` from `plugin/nf-core-utils`                                         |
| `softwareVersionsToYAML(ch_versions)`      | `softwareVersionsToYAML(softwareVersions: ch_versions, nextflowVersion: workflow.nextflow.version)` |
| `processVersionsFromFile`                  | `softwareVersionsToYAML(softwareVersions: ...)`, after checking the input representation            |
| `paramsSummaryMultiqc(summary_params)`     | `paramsSummaryMultiqc(summary_params)` from `plugin/nf-core-utils`                                  |
| `methodsDescriptionText(mqc_methods_yaml)` | `methodsDescriptionText(mqc_methods_yaml.toString())` for an uncustomised template                  |

nf-core-utils 0.7.0 retains `softwareVersionsToYAML` but deprecates it in favour of `collectVersions`. Choose the API supported by the target release and verify its input and return types. Do not combine a version-channel redesign with a helper replacement unless required.

Delete `toolCitationText` and `toolBibliographyText` only if they are unused template stubs. Preserve populated citations and pipeline-specific template substitutions. See [the citations reference](citations.md) for a separate citation migration.
