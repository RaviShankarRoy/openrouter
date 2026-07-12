# syntax=docker/dockerfile:1.7
# Multi-stage: build a static binary, ship it on scratch. Final image < 30MB (DRD §22.2).

FROM golang:1.24-alpine AS build
WORKDIR /src
RUN apk add --no-cache git ca-certificates
COPY go.mod go.sum ./
RUN go mod download
COPY . .
ARG VERSION=dev
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build -trimpath \
        -ldflags "-s -w -X main.version=${VERSION}" \
        -o /out/gateway ./cmd/gateway

FROM scratch
COPY --from=build /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=build /out/gateway /gateway
COPY --from=build /src/configs /configs
EXPOSE 8080 9091
USER 65532:65532
ENTRYPOINT ["/gateway"]
