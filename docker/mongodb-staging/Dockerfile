FROM scratch AS yaml-package

ADD --checksum=sha256:7f005cf0b8ee639b4557e0e321dc067c1f2aa0a442d096e03f2ab53353738794 \
    https://registry.npmjs.org/js-yaml/-/js-yaml-3.15.2.tgz /js-yaml.tgz

FROM mongo@sha256:d819ca7f8e564eb253ae6dc9cac330386c56e6919f3570a74c04f04679433117

ENV JSYAML_VERSION=3.15.2 \
    JSYAML_CHECKSUM=7f005cf0b8ee639b4557e0e321dc067c1f2aa0a442d096e03f2ab53353738794
ARG SOURCE_DATE_EPOCH=1795219200

RUN --mount=type=bind,from=yaml-package,source=/js-yaml.tgz,target=/run/js-yaml.tgz,readonly \
    set -eux; \
    echo "$JSYAML_CHECKSUM  /run/js-yaml.tgz" | sha256sum -c -; \
    test -L /js-yaml.js; \
    test "$(readlink /js-yaml.js)" = /opt/js-yaml/dist/js-yaml.js; \
    tar -xzf /run/js-yaml.tgz --no-same-owner --strip-components=1 -C /opt/js-yaml \
        package/dist/js-yaml.js package/package.json package/LICENSE; \
    touch -d "@$SOURCE_DATE_EPOCH" /opt/js-yaml /opt/js-yaml/dist; \
    test "$(jq -r .version /opt/js-yaml/package.json)" = "$JSYAML_VERSION"
