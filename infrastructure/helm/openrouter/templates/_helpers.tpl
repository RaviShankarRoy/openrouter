{{/*
Common helpers. Stay small — avoid Helm-as-templating-language anti-patterns.
*/}}

{{/* Chart name truncated to 63 chars (k8s label limit). */}}
{{- define "openrouter.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/* Fully qualified app name (release-aware). */}}
{{- define "openrouter.fullname" -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/* Chart label string used in metadata. */}}
{{- define "openrouter.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/* Standard labels applied to every resource. */}}
{{- define "openrouter.labels" -}}
helm.sh/chart: {{ include "openrouter.chart" . }}
app.kubernetes.io/name: {{ include "openrouter.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: openrouter
{{- with .Values.global.commonLabels }}
{{ toYaml . }}
{{- end }}
{{- end -}}

{{/* Component-specific labels: usage `{{ include "openrouter.componentLabels" (dict "ctx" . "component" "gateway") }}` */}}
{{- define "openrouter.componentLabels" -}}
{{ include "openrouter.labels" .ctx }}
app.kubernetes.io/component: {{ .component }}
{{- end -}}

{{/* Selector labels — must remain stable across upgrades or selector mismatches break. */}}
{{- define "openrouter.selectorLabels" -}}
app.kubernetes.io/name: {{ include "openrouter.name" .ctx }}
app.kubernetes.io/instance: {{ .ctx.Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end -}}

{{/* Image string with digest fallback. */}}
{{- define "openrouter.image" -}}
{{- $registry := .ctx.Values.global.imageRegistry -}}
{{- $repo := .image.repository -}}
{{- $tag := default .ctx.Chart.AppVersion .image.tag -}}
{{- printf "%s/%s:%s" $registry $repo $tag -}}
{{- end -}}

{{/* Service account name per component. */}}
{{- define "openrouter.serviceAccountName" -}}
{{- printf "%s-%s" (include "openrouter.fullname" .ctx) .component | trunc 63 | trimSuffix "-" -}}
{{- end -}}
