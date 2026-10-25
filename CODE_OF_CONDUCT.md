# Vectronyx AI Workbench — Code of Conduct

## Our Pledge

We as members, contributors, and maintainers of **Vectronyx AI Workbench** pledge to make participation in our community and development lifecycle a harassment-free, intellectually rigorous, collaborative, and professional experience for everyone, regardless of age, body size, visible or invisible disability, ethnicity, sex characteristics, gender identity and expression, level of experience, education, socio-economic status, nationality, personal appearance, race, caste, color, religion, or sexual identity and orientation.

We pledge to act and interact in ways that contribute to an open, welcoming, diverse, inclusive, and healthy community where technical excellence and mutual respect thrive in equal measure.

---

## Our Standards

### 1. Professional & Constructive Engineering Culture
Examples of behavior that contributes to a positive environment for our project:
- **Demonstrating empathy and kindness** toward other people, whether junior apprentices or senior staff architects.
- **Focusing on objective, evidence-based technical discourse**: Critique the architecture, the code patterns, the latency characteristics, or the algorithmic complexity—never the person.
- **Respectful peer review**: Providing thorough, actionable, constructive, and courteous feedback during pull request (PR) reviews.
- **Gracefully accepting constructive criticism**: Valuing collaborative iteration, performance profiling data, and architecture reviews as mechanisms for collective growth.
- **Transparency and accountability**: Owning outages, regression bugs, and oversights without shifting blame, focusing on blameless postmortems and architectural remediation.

### 2. Unacceptable Behaviors
Examples of unacceptable behavior include:
- The use of sexualized language or imagery, and sexual attention or advances of any kind.
- Trolling, insulting or derogatory comments, and personal or political attacks.
- Public or private harassment, doxxing, or publishing private technical/personal credentials.
- Continued technical gatekeeping, dismissive behavior towards novice inquiries, or condescending commentary.
- Deliberate introduction of malicious code, backdoors, spyware, prompt-injection vectors, or insecure dependencies.
- Plagiarism of copyrighted codebases without attribution or violating open-source licensing.

### 3. Responsible AI & Data Ethics Standards
As an autonomous AI workbench handling agentic web interactions, vector stores, and private tabular datasets, contributors must uphold strict AI ethical boundaries:
- **Zero Data Poisoning**: No agent workflows or test fixtures may intentionally scrape, harvest, or index non-consensual personally identifiable information (PII).
- **Safety in Autonomous Tool Calling**: Tool integrations (scrapers, shell executors, database mutation endpoints) must implement sandboxing, strict parameter coercion, idempotency keys, and explicit circuit breakers to prevent denial of service or runaway autonomous loops.
- **Privacy First**: Sensitive client datasets, database connection credentials, and LLM API keys must never be hardcoded, logged in plain text, or leaked across multi-tenant boundaries.

---

## Enforcement Responsibilities

Community maintainers and project leadership are responsible for clarifying and enforcing our standards of acceptable behavior. They have the right and responsibility to remove, edit, or reject comments, commits, code reviews, issues, and pull requests that do not adhere to this Code of Conduct.

Maintainers are also empowered to communicate the reasons for moderation actions when appropriate, while safeguarding the privacy and safety of affected reporters.

---

## Scope

This Code of Conduct applies within all project spaces—including GitHub repositories, issue trackers, pull requests, project discussion forums, team chat spaces, and any official Vectronyx virtual or physical meetups. It also applies when an individual is officially representing the project in public spaces.

---

## Reporting & Incident Escalation

Instances of abusive, harassing, or otherwise unacceptable behavior may be reported to the Vectronyx Maintainer Team at:

📧 **conduct@vectronyx.dev** *(or open an issue marked `confidential:maintainers-only`)*

All reports will be reviewed and investigated promptly and fairly. The maintainer team is obligated to respect the privacy and security of the reporter of any incident.

### Enforcement Tiers

Maintainers will follow these Community Impact Guidelines in determining the consequences for any action deemed in violation:

1. **Correction**:
   - **Impact**: Use of inappropriate language or other behavior deemed unprofessional or unwelcome in the community.
   - **Consequence**: A private, written warning from maintainers, providing clarity around the violation and an explanation of why the behavior was inappropriate. A public apology may be requested.
2. **Warning**:
   - **Impact**: A violation through a single incident or series of actions demonstrating pattern disregard for community standards.
   - **Consequence**: A formal written warning with consequences for continued behavior. No interaction with the people involved or the project spaces for a specified period (14 days).
3. **Temporary Ban**:
   - **Impact**: A serious violation of community standards, including sustained harassment, security bypasses, or aggressive hostility.
   - **Consequence**: A temporary ban from any sort of interaction or public communication with the community for a specified period (30–90 days).
4. **Permanent Expulsion**:
   - **Impact**: Demonstrating a pattern of violation, including sustained harassment, intentional introduction of vulnerabilities, hate speech, or fraud.
   - **Consequence**: A permanent ban from any sort of public or private contribution to the Vectronyx project ecosystem.

---

## Attribution

This Code of Conduct is adapted from the [Contributor Covenant](https://www.contributor-covenant.org), version 2.1, with added guidelines for **Responsible AI Engineering, Agentic Tool Safety, and Data Governance**.
