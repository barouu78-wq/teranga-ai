# Teranga AI — Autonomous SEO Agent (foundation)

## What this first iteration does

The scheduled GitHub Actions workflow runs every day at 06:17 UTC and can also be started manually. It checks:

- HTTP availability of the homepage, `/robots.txt`, and `/sitemap.xml`
- Sitemap XML validity and same-site URL discovery
- Up to 40 URLs from the sitemap (plus the homepage)
- HTTP status, response time, title, meta description, canonical link, and H1 count
- A JSON report uploaded as a GitHub Actions artifact for 30 days

The monitor uses Python's standard library and requires no API key or additional dependency. Missing metadata is reported as a warning; site/network and sitemap errors fail the job.

## Safety boundaries

This iteration is read-only. It does not edit production pages, publish generated content, create backlinks, or change DNS/deployment settings. It does not promise ranking positions. Review findings before making changes; Google states that indexing and ranking are not guaranteed and changes can take weeks or months to evaluate.

## Next steps toward a genuine AI agent

1. Review the first scheduled/manual report and tune false positives.
2. Verify whether the existing Search Console setup is only site verification in Google, or whether Teranga AI already has authorized API access. A verified property does not automatically give this codebase API access.
3. If API access is not already implemented, add it through an authorized service account or OAuth integration with least-privilege access. Never commit credentials.
4. Compare query/page impressions, clicks, CTR, average position, and country/device segments to prioritize real opportunities.
5. Have an LLM propose specific, evidence-based fixes and content briefs; require tests and human approval before publishing.
6. Create a PR for each code/content change and require CI to pass. Never automatically merge or deploy an unreviewed SEO change.
7. Track outcomes over 28-day windows and keep a change log.

## Initial keyword clusters

- Brand/product: Teranga AI, assistant IA Sénégal, intelligence artificielle Sénégal
- Practical life: transport Dakar, météo Dakar, régions du Sénégal
- Travel: visiter Dakar, île de Gorée, guide touristique Sénégal, hôtels au Sénégal
- Diaspora and business: diaspora sénégalaise, créer une entreprise au Sénégal, opportunités au Sénégal

These are starting hypotheses, not validated search-volume data. Validate them against Search Console and keyword research before building pages. Avoid thin doorway pages or repeated city pages with near-identical text; every page should answer a distinct user need with accurate local information.

## How to run it

- GitHub: Actions → SEO Monitor → Run workflow
- Download the `teranga-ai-seo-report` artifact from the run summary.
- Fix critical availability/sitemap errors first, then prioritize repeated metadata and content issues.

## References

- Google SEO Starter Guide: https://developers.google.com/search/docs/fundamentals/seo-starter-guide?hl=fr
- Google developer SEO guide: https://developers.google.com/search/docs/fundamentals/get-started-developers?hl=fr
- Sitemap best practices: https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap
