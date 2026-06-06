import { NextRequest, NextResponse } from 'next/server';

const REPO_MAP: Record<string, string> = {
  alpha: 'specimba/nexusalpha',
  dashboards: 'specimba/nexusdashboards',
};

async function fetchPulls(repo: string, token: string) {
  const res = await fetch(
    `https://api.github.com/repos/${repo}/pulls?state=open&per_page=50`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
      },
      next: { revalidate: 30 },
    }
  );

  if (!res.ok) {
    const error = await res.text();
    throw new Error(`GitHub API error for ${repo}: ${res.status} - ${error}`);
  }

  const pulls = await res.json();

  return pulls.map((pr: Record<string, unknown>) => ({
    number: pr.number,
    title: pr.title,
    state: pr.state,
    user: (pr.user as Record<string, string> | null)?.login ?? 'unknown',
    created_at: pr.created_at,
    updated_at: pr.updated_at,
    commits: pr.commits,
    additions: pr.additions,
    deletions: pr.deletions,
    changed_files: pr.changed_files,
    mergeable: pr.mergeable,
    mergeable_state: pr.mergeable_state,
    head_ref: (pr.head as Record<string, string>)?.ref ?? '',
    base_ref: (pr.base as Record<string, string>)?.ref ?? '',
    body_preview:
      typeof pr.body === 'string' ? pr.body.slice(0, 300) : null,
    html_url: pr.html_url,
    repo,
  }));
}

export async function GET(request: NextRequest) {
  const token = process.env.GITHUB_TOKEN;

  if (!token) {
    return NextResponse.json(
      { error: 'GITHUB_TOKEN is not configured' },
      { status: 500 }
    );
  }

  const { searchParams } = request.nextUrl;
  const repoParam = searchParams.get('repo') ?? 'all';

  let targetRepos: Array<{ key: string; fullName: string }>;

  if (repoParam === 'all') {
    targetRepos = Object.entries(REPO_MAP).map(([key, fullName]) => ({
      key,
      fullName,
    }));
  } else if (REPO_MAP[repoParam]) {
    targetRepos = [{ key: repoParam, fullName: REPO_MAP[repoParam] }];
  } else {
    return NextResponse.json(
      {
        error: `Invalid repo parameter. Use "alpha", "dashboards", or "all".`,
      },
      { status: 400 }
    );
  }

  try {
    const results = await Promise.allSettled(
      targetRepos.map(({ fullName }) => fetchPulls(fullName, token))
    );

    const pulls: Record<string, unknown[]> = {};
    let total = 0;

    results.forEach((result, index) => {
      const { key } = targetRepos[index];
      if (result.status === 'fulfilled') {
        pulls[key] = result.value;
        total += result.value.length;
      } else {
        pulls[key] = [];
      }
    });

    return NextResponse.json({ pulls, total });
  } catch (error) {
    return NextResponse.json(
      {
        error: 'Failed to fetch pull requests',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}
