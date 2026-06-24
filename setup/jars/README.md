# Pre-Built JARs

The catch-up script downloads Mule app JARs automatically from GitHub Releases.

**Release tag**: `course-v1.0`
**Expected files**:
- `slack-agent-router.jar`
- `ai-orchestrator.jar`
- `data-cloud-sapi.jar`
- `service-cloud-mcp.jar`

## Building from source

If you want to build JARs yourself instead of using the pre-built release:

```bash
cd slack-agent-router && mvn package -DskipTests && cp target/*.jar ../setup/jars/slack-agent-router.jar
cd ai-orchestrator   && mvn package -DskipTests && cp target/*.jar ../setup/jars/ai-orchestrator.jar
cd data-cloud-sapi   && mvn package -DskipTests && cp target/*.jar ../setup/jars/data-cloud-sapi.jar
cd service-cloud-mcp && mvn package -DskipTests && cp target/*.jar ../setup/jars/service-cloud-mcp.jar
```

## Updating the release (ops)

```bash
# Tag the release
git tag course-v1.1
git push origin course-v1.1

# Upload JARs via GitHub CLI
gh release create course-v1.1 --title "Course v1.1" \
  setup/jars/slack-agent-router.jar \
  setup/jars/ai-orchestrator.jar \
  setup/jars/data-cloud-sapi.jar \
  setup/jars/service-cloud-mcp.jar
```

Then update `stable.course.jarReleaseTag` in `student.template.json` to `course-v1.1`.

## .gitignore note

Actual `.jar` files are gitignored. Only this README is committed to the repo.
