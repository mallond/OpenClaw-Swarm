# README-About-Swarm

A quick Docker Swarm reference in practical "docker-speak" for this project.

## Core Concepts

- **Swarm** — A cluster of Docker engines operating together as one orchestration system.
- **Node** — A machine participating in the swarm.
- **Manager node** — A node that maintains cluster state and makes orchestration decisions.
- **Worker node** — A node that runs tasks assigned by managers.
- **Leader** — The manager currently elected to coordinate swarm management through Raft.
- **Raft** — The consensus protocol managers use to keep swarm state consistent.
- **Quorum** — The minimum number of managers required to agree on cluster state changes.

## Workloads and Desired Behavior

- **Service** — The declarative definition of how containers should run in the swarm.
- **Task** — A single scheduled instance of a service container on a node.
- **Replica** — One desired running copy of a service.
- **Replicated service** — A service configured to run a specified number of replicas.
- **Global service** — A service configured to run exactly one task on every eligible node.
- **Stack** — A group of services, networks, and configs deployed together, usually from a Compose file.
- **Desired state** — The target configuration the swarm tries to maintain.
- **Actual state** — The real current condition of services and tasks in the cluster.
- **Reconciliation** — The manager process that continuously adjusts actual state toward desired state.
- **Scheduler** — The swarm component that decides where tasks should be placed.

## Placement and Node Control

- **Placement constraint** — A hard rule limiting which nodes may run a task.
- **Placement preference** — A soft rule influencing task distribution across nodes.
- **Label** — Metadata attached to nodes or objects for filtering and placement logic.
- **Availability** — A node state controlling whether it can receive tasks.
- **Active** — A node availability state allowing normal task scheduling.
- **Pause** — A node availability state preventing new tasks while leaving existing ones running.
- **Drain** — A node availability state that removes existing tasks and blocks new ones.

## Networking and Service Discovery

- **Overlay network** — A multi-host virtual network used for communication across swarm nodes.
- **Ingress network** — The special overlay network used for published service traffic and routing mesh.
- **Routing mesh** — The swarm traffic layer that accepts published port requests on any node and routes them to service tasks.
- **Publish port** — A port exposed externally by a swarm service.
- **Internal port** — The port the container listens on inside the service task.
- **Endpoint mode** — The method swarm uses to expose service discovery to clients.
- **VIP** — Virtual IP mode where a service gets a single internal IP for load-balanced access.
- **DNSRR** — DNS round-robin mode where service discovery returns multiple task IPs directly.

## Updates and Lifecycle

- **Slot** — The stable ordinal position of a replica within a replicated service.
- **Rolling update** — A controlled process for replacing service tasks with new versions incrementally.
- **Rollback** — Reverting a service to its previous configuration after an update issue.
- **Health check** — A container-level test used to determine whether a task is healthy.

## Config, Secrets, and Trust

- **Secret** — Sensitive data distributed securely to services at runtime.
- **Config** — Non-sensitive configuration data distributed to services by the swarm.
- **Join token** — A token used by new nodes to join the swarm as worker or manager.
- **Swarm CA** — The certificate authority that issues node certificates for swarm trust.
- **mTLS** — Mutual TLS used for encrypted and authenticated communication between swarm nodes.
- **Autolock** — A security feature that requires an unlock key after manager restart to access Raft data.
- **Unlock key** — The key required to unlock an autolocked manager.

## Swarm Networking Addresses and Internal Components

- **Advertise address** — The network address a node tells other nodes to use for communication.
- **Listen address** — The local address a node binds to for swarm control traffic.
- **Dispatcher** — The manager component that assigns tasks and monitors worker status.
- **Allocator** — The manager component that assigns network and resource-related settings to swarm objects.
- **Control plane** — The management communication path for orchestration and cluster state.
- **Data plane** — The application traffic path used by running service containers.

## Task States You’ll See

- **Pending** — A task state indicating it has been accepted but not yet scheduled or started.
- **Running** — A task state indicating the container is currently executing.
- **Shutdown** — A task state indicating the task has been intentionally stopped.
- **Failed** — A task state indicating the task exited unexpectedly or could not start.
- **Orphaned task** — A task left behind or disconnected from expected management state, usually after failures or node issues.

## Cluster Communication and Operations

- **Gossip** — The peer-to-peer mechanism used to distribute certain network state across nodes.
- **Swarm init** — The action that creates a new swarm and promotes the first node to manager.
- **Swarm join** — The action that adds a node to an existing swarm.
- **Swarm leave** — The action that removes a node from the swarm.
- **Swarm update** — The action that modifies swarm-wide settings.
- **Node promote** — The action that changes a worker into a manager.
- **Node demote** — The action that changes a manager into a worker.
- **Service scale** — The action of changing the number of replicas for a replicated service.
- **Service update** — The action of changing service configuration, image, ports, or placement rules.
- **Service inspect** — Viewing the detailed configuration and current state of a service.
- **Stack deploy** — Deploying a stack definition into the swarm.
- **Stack rm** — Removing a deployed stack and its swarm-managed resources.

---

## Other Experiments

- Dual-rack Docker-in-Docker swarm simulation (**Machine Rack 1 / Machine Rack 2**)
- Cross-rack **Revolt** task handoff (state transfer + snapshot/restore)
- Per-task ARM events with aggregated scoreboard
- Leader/follower game loops (RPS/duel) in replicated services
- Embedded per-task PicoClaw runtime with shared Ollama backend
