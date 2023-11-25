## Boid_v0

### Artifacts

- `myBoid`

## Anyboid_v0

- boid registry: a noSQL table of all active anymoids
    - centralized (distributed on v1)
- agent servers
    - `ws://modalities/<modality-name>/{pub,sub}`
    - agent intelligence
    - centralized (distributed on boids themselves or other servers in v1)
    - the cluster runs on a few hosts, so we consolidate on GPU usage
    - has a user connection to the pg database
- supabase auth / pg / storage
    - agent servers save their modality episodes here (in v1, they do it for a training profit)
    - `https://<hostname>/<boid-name>/<res_glob>` for sharable resources. Names must be unique and some are set aside for the system namespace
    - `api.<hostname>/<ehatever>` for api commands

### Artifacts

- `robot-client-rpi`
- `robot-client-esp32`
- `myBoid` (fork of Boid_v0/myBoid) with 