FROM debian:bookworm-slim@sha256:3783cc01769c7b2b1b83a5c5ad96c815348e28ed7da68e2e3687004faa906251

ARG IMPACKET_VERSION=0.13.1
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        dbus \
        dbus-x11 \
        freerdp2-x11 \
        libpam-modules \
        openssl \
        pamtester \
        procps \
        python3 \
        python3-pip \
        ssl-cert \
        x11-xserver-utils \
        xorgxrdp \
        xrdp \
        xterm \
        xvfb \
    && python3 -m pip install --break-system-packages --no-cache-dir \
        "impacket==${IMPACKET_VERSION}" \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 --shell /bin/bash q60t \
    && adduser xrdp ssl-cert \
    && install -d -o q60t -g q60t -m 0750 /srv/q60t-share \
    && printf '%s\n' 'Disposable tiz0wn validation share.' > /srv/q60t-share/README.txt \
    && chown q60t:q60t /srv/q60t-share/README.txt

COPY xrdp-sesman.pam /etc/pam.d/xrdp-sesman
COPY startwm.sh /etc/xrdp/startwm.sh
COPY entrypoint.sh /usr/local/sbin/tiz0wn-lab-entrypoint
COPY client.py /usr/local/lib/tiz0wn-lab-client.py
COPY server.py /usr/local/lib/tiz0wn-lab-server.py
COPY client.sh /usr/local/sbin/tiz0wn-lab-client
COPY healthcheck.sh /usr/local/sbin/tiz0wn-lab-healthcheck

RUN chmod 0644 /etc/pam.d/xrdp-sesman \
    && chmod 0755 /etc/xrdp/startwm.sh /usr/local/sbin/tiz0wn-lab-entrypoint \
        /usr/local/sbin/tiz0wn-lab-client /usr/local/sbin/tiz0wn-lab-healthcheck \
    && chmod 0644 /usr/local/lib/tiz0wn-lab-client.py \
        /usr/local/lib/tiz0wn-lab-server.py

EXPOSE 3389 445

HEALTHCHECK --interval=5s --timeout=2s --start-period=2s --retries=12 \
    CMD ["/usr/local/sbin/tiz0wn-lab-healthcheck"]

ENTRYPOINT ["/usr/local/sbin/tiz0wn-lab-entrypoint"]
