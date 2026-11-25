FROM docker.io/library/golang:1.26.11-bookworm@sha256:66c04b389c4b0a2e0f0d51f3a37de0109650887a321b2a3b8cd9f573d7490a01 AS build
ENV GOTOOLCHAIN=local CGO_ENABLED=0
WORKDIR /src
ADD https://github.com/caddyserver/caddy.git#679806f92d49e5b494200f2e90a93f228203a418 ./
RUN go mod download && go mod verify
RUN --network=none go build -mod=readonly -trimpath -buildvcs=false -ldflags="-s -w" -o /out/caddy ./cmd/caddy

FROM scratch
COPY --chmod=0555 --from=build /out/caddy /usr/bin/caddy
COPY --chmod=0444 --from=build /src/LICENSE /usr/share/licenses/caddy/LICENSE
ENV PATH=/usr/bin
LABEL org.opencontainers.image.licenses=Apache-2.0 \
      org.opencontainers.image.source=https://github.com/caddyserver/caddy \
      org.opencontainers.image.revision=679806f92d49e5b494200f2e90a93f228203a418
USER 10001:10001
ENTRYPOINT ["/usr/bin/caddy"]
