{{- define "credit-applications-hub.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "credit-applications-hub.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name (include "credit-applications-hub.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "credit-applications-hub.labels" -}}
app.kubernetes.io/name: {{ include "credit-applications-hub.name" . }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "credit-applications-hub.selectorLabels" -}}
app.kubernetes.io/name: {{ include "credit-applications-hub.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "credit-applications-hub.componentName" -}}
{{- printf "%s-%s" (include "credit-applications-hub.fullname" .context) .name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "credit-applications-hub.databaseHost" -}}
{{- printf "%s-postgres" (include "credit-applications-hub.fullname" .) -}}
{{- end -}}

{{- define "credit-applications-hub.redisHost" -}}
{{- printf "%s-redis" (include "credit-applications-hub.fullname" .) -}}
{{- end -}}

{{- define "credit-applications-hub.rabbitmqHost" -}}
{{- printf "%s-rabbitmq" (include "credit-applications-hub.fullname" .) -}}
{{- end -}}

{{- define "credit-applications-hub.backendHost" -}}
{{- printf "%s-backend" (include "credit-applications-hub.fullname" .) -}}
{{- end -}}

{{- define "credit-applications-hub.mockProviderHost" -}}
{{- printf "%s-mock-provider" (include "credit-applications-hub.fullname" .) -}}
{{- end -}}

{{- define "credit-applications-hub.commonEnvConfigMapName" -}}
{{- printf "%s-env" (include "credit-applications-hub.fullname" .) -}}
{{- end -}}

{{- define "credit-applications-hub.commonEnvSecretName" -}}
{{- printf "%s-secrets" (include "credit-applications-hub.fullname" .) -}}
{{- end -}}
