# Development

The project requires Python 3.12 or newer and uses `uv` for dependency
management.

## Set up

Use the repository virtual environment:

```bash
make install-dev
make install-docs
```

## Validate

Run offline tests and documentation examples:

```bash
make test
```

Build the documentation with strict link and configuration checks:

```bash
make docs
```

Preview it locally:

```bash
make docs-serve
```

Normal tests do not access CMS. Live CMS tests are marked `live_cms` and run
only through the explicitly requested live integration workflow or
`make test-live`.

The live suite is divided into catalog, fresh-current, historical, and
exhaustive lanes. See
[Testing CMS compatibility](testing.md) for their scope, schedules, cache
policy, and maintenance instructions.

## Documentation deployment

Pull requests build the site without deploying it. A push to `main` builds the
same site and deploys it through GitHub Actions to GitHub Pages.

The repository's **Settings → Pages → Build and deployment → Source** must be
set to **GitHub Actions**.
