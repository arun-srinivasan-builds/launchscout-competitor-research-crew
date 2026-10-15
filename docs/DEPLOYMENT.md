# DEPLOYMENT — LaunchScout public demo (Docker + existing Traefik)

> Status: **prepared, not deployed.** The image was built and validated locally (see
> `docs/QUALITY_REPORT.md`, "M8"). Nothing here has been run on the VPS. Network, entrypoint
> and certificate-resolver names are **not assumed**: read them from the running Traefik first
> and supply them as variables.

The deployment is **demo-only**: `LAUNCHSCOUT_MODE=demo`, saved runs baked into the image, no
API keys, read-only filesystem, no published port. Never give it `OPENAI_API_KEY` or
`SERPER_API_KEY`.

## 0. Rules for a shared VPS

- Do **not** modify or restart Traefik or any existing application.
- Do **not** add another reverse proxy. Traefik routes the host from Docker labels.
- Do **not** publish port 8501 on the host. The container is reachable only on Traefik's network.
- Everything up to step 4 is read-only. Do not assume the VPS is empty.

## 1. DNS

Create an `A` record (and `AAAA` if the VPS has IPv6) for `launchscout.arunsrinivasan.io`
pointing to the VPS public IP. Check: `dig +short launchscout.arunsrinivasan.io` returns it.
Use a short TTL (300 s) until the first certificate is issued.

## 2. Discover the Traefik settings (read-only)

```bash
docker ps --format '{{.Names}}\t{{.Image}}\t{{.Ports}}' | grep -i traefik
T=<traefik-container-name>
docker inspect "$T" --format '{{range $n,$v := .NetworkSettings.Networks}}{{$n}}{{"\n"}}{{end}}'
docker inspect "$T" --format '{{json .Args}}'
docker inspect "$T" --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{"\n"}}{{end}}'
```

If Traefik is configured by a static file, read it from the mount shown above.

| Variable | Where it comes from |
|---|---|
| `TRAEFIK_NETWORK` | the shared Docker network Traefik is attached to (the one existing apps use) |
| `TRAEFIK_ENTRYPOINT` | `entrypoints.<name>.address=:443`, the HTTPS entrypoint |
| `TRAEFIK_CERT_RESOLVER` | `certificatesresolvers.<name>.acme...` |
| Docker provider | `providers.docker`; note `exposedbydefault` and any `providers.docker.network` |

Also read the labels of one existing app
(`docker inspect <app> --format '{{json .Config.Labels}}'`) and match its conventions.
Check that the router name `launchscout` is unused:
`docker ps -q | xargs docker inspect --format '{{json .Config.Labels}}' | grep -c 'routers.launchscout'`
should print `0`.

## 3. Prepare

```bash
git clone https://github.com/arun-srinivasan-builds/launchscout-competitor-research-crew.git
cd launchscout-competitor-research-crew
git checkout <release-tag-or-commit>
```

Create `deploy/.env.traefik` (names only, no secrets; do not commit it):

```
TRAEFIK_NETWORK=<from step 2>
TRAEFIK_ENTRYPOINT=<from step 2>
TRAEFIK_CERT_RESOLVER=<from step 2>
LAUNCHSCOUT_HOST=launchscout.arunsrinivasan.io
LAUNCHSCOUT_TAG=<tag or short commit>
```

The compose file pins the project name `launchscout-demo` (`name:` at the top), so Compose never
uses the directory name `deploy` and cannot clash with another stack. Container, image and
router names are also `launchscout-*`. Confirm no existing project uses it:
`docker compose ls -a` must not list `launchscout-demo`, and `docker ps -a --filter name=launchscout-demo -q`
must print nothing, before the first deploy.

Render and review before starting. Compose refuses to render if a variable is missing:

```bash
docker compose --env-file deploy/.env.traefik -f deploy/docker-compose.traefik.yml config
```

Confirm in the output: no `ports:` section, one external network equal to `TRAEFIK_NETWORK`,
`name: launchscout-demo`, `LAUNCHSCOUT_MODE: demo`, and the router rule `Host(launchscout.arunsrinivasan.io)`.

## 4. Deploy

```bash
docker compose --env-file deploy/.env.traefik -f deploy/docker-compose.traefik.yml build
docker compose --env-file deploy/.env.traefik -f deploy/docker-compose.traefik.yml up -d
```

Traefik discovers the container from its labels; it is not restarted or reconfigured. The
first request may wait up to a minute while the certificate is issued.

## 5. Validate

```bash
docker ps --filter name=launchscout-demo --format '{{.Status}}'      # Up ... (healthy)
curl -sI https://launchscout.arunsrinivasan.io/ | head -5            # 200, valid certificate
curl -s  https://launchscout.arunsrinivasan.io/_stcore/health        # ok
curl -sI --max-time 5 http://<VPS-IP>:8501/                          # must fail: not published
docker inspect launchscout-demo --format '{{json .HostConfig.PortBindings}}'   # {} or null
docker inspect launchscout-demo --format '{{.HostConfig.ReadonlyRootfs}}'      # true
```

In a browser: the demo banner is shown, "Run research" is disabled, two saved runs are listed,
replay works, Weekly Tracking shows the L5 vs L6 comparison and downloads work. Streamlit uses
WebSockets, which Traefik proxies without extra middleware.

## 6. Firewall

Only SSH, 80 and 443 should be reachable from the internet (80/443 are already needed by
Traefik). Do not open 8501: `ss -ltnp | grep 8501` must show nothing for this app. Do not alter
rules that other applications rely on.

## 7. Rollback

Existing applications are untouched, so rollback only removes this service:

```bash
docker compose --env-file deploy/.env.traefik -f deploy/docker-compose.traefik.yml down
```

Traefik drops the router when the container stops. To return to an earlier version, set
`LAUNCHSCOUT_TAG`, `git checkout <previous-tag>` and repeat step 4. Remove an image with
`docker image rm launchscout-demo:<tag>`. DNS may stay; the host then returns Traefik's 404.

## 8. Updating the demo

Saved runs are baked into the image, so rebuild to change them. Add a run to
`demo_data/saved_runs/` deliberately (see `demo_data/README.md`), run the test suite (it checks
the demo data for secrets and the expected file set) and redeploy from a new tag.

## Local check of the same image

```bash
docker compose build && docker compose up -d     # binds 127.0.0.1:8501 (change the host port if taken)
curl -s http://127.0.0.1:8501/_stcore/health
```
