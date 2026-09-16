---
name: nf-core-containers
description: Choose, pin, validate, and troubleshoot containers for nf-core modules and pipelines. Use when editing module conda/container directives, environment.yml, Dockerfiles, Seqera Containers URLs, BioContainers/mulled images, container configs, or offline/container-profile docs.
license: MIT
metadata:
  author: nf-core
  version: "0.1.0"
  nf_core_tools_version: "4.0.2"
---

# nf-core containers

Use this skill when adding or changing software dependencies, container directives, `environment.yml`, custom `Dockerfile`s, generated container config files, or runtime container profiles in nf-core projects.

## Core rules

- nf-core pipelines must run with `-profile docker` and all software requirements satisfied.
- Pin specific, stable container/software versions. Never use `latest`, `dev`, `master`, floating tags, or unversioned images.
- Prefer Bioconda / Conda-forge packages so Docker and Singularity/Apptainer images can be generated reproducibly.
- For nf-core modules, define software in both:
  - `environment.yml` next to `main.nf`
  - the process `conda` and `container` directives in `main.nf`
- Pin Conda packages by channel and version, e.g. `bioconda::fastqc=0.11.9`; do not pin Conda build strings because they can vary by platform.
- Use custom Dockerfiles only when software cannot reasonably be packaged on Bioconda / Conda-forge.

## Standard module pattern

```groovy
conda "bioconda::fastqc=0.11.9"
container "${ workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container ?
    'https://depot.galaxyproject.org/singularity/fastqc:0.11.9--0' :
    'biocontainers/fastqc:0.11.9--0' }"
```

Notes:

- Docker/BioContainers names typically omit the registry prefix unless a full URI is required.
- Singularity/Apptainer URLs commonly use `https://depot.galaxyproject.org/singularity/...` or Seqera Containers HTTPS URLs.
- Keep container versions in sync with version reporting outputs in `main.nf` and `meta.yml`.

## Seqera Containers workflow

Use Seqera Containers when BioContainers is unavailable, insufficient, or when generating combined Docker and Singularity images from Conda packages.

1. Verify the module `environment.yml` installs locally or is otherwise coherent.
2. Open Seqera Containers and enter the required Conda packages.
3. Generate the Docker URL and copy it without `https://`.
4. Generate the Singularity URL, wait for the build, enable HTTPS, and copy the full `https://...` URL.
5. Use the nf-core conditional container directive:

```groovy
container "${ workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container ?
    'https://community-cr-prod.seqera.io/<singularity-container-id>' :
    'community.wave.seqera.io/<docker-container-id>' }"
```

Important: Docker URLs should not include `https://`; Singularity URLs should.

## Multi-tool containers

- Avoid bundling unrelated tools. A module should normally wrap one command or one coherent subcommand.
- If a pipeline genuinely needs a multi-tool container, search existing mulled containers first:

```console
mulled-search --destination quay singularity --channel bioconda --search bowtie samtools | grep "mulled"
```

- Validate the container contents by inspecting `/usr/local/conda-meta/history` inside the image.
- If no existing image works, propose a change to BioContainers `multi-package-containers` rather than inventing an ad-hoc image.

## Custom containers

Use a module-local `Dockerfile` only when the tool is not available on Bioconda / Conda-forge and cannot reasonably be added.

Checklist:

- Discuss custom containers with nf-core maintainers for shared components.
- Pin every base image and installed software version.
- Avoid external downloads without checksums.
- Ensure the image can report tool versions for topic-based version outputs.
- Prefer mirroring important custom images to a stable nf-core-controlled registry for reproducibility.

## Runtime troubleshooting

- If tools are missing, ensure the run used a container/environment profile such as `-profile docker`, `-profile singularity`, or `-profile conda`.
- Enable only one container engine in a profile unless there is a deliberate reason.
- If Docker processes fail because `$HOME` is unwritable, override `containerOptions` for the affected process rather than disabling user mapping globally.
- If a container needs network access under Docker, consider process-specific `containerOptions = '--network host'`.
- For offline runs, use `nf-core pipelines download` with the desired container type and transfer the pipeline bundle, containers, and reference data together.

## Validation commands

```bash
nf-core modules lint <tool>/<subtool>
nf-core pipelines lint -k container_configs
nf-core pipelines lint
NXF_SYNTAX_PARSER=v2 nextflow lint <component-path>
```

Review generated `conf/` container config changes after module/container edits.
