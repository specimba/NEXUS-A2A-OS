import { NextResponse } from 'next/server';

const REPOS = ['specimba/nexusalpha', 'specimba/nexusdashboards'];

async function fetchBranches(repo: string, token: string) {
  const res = await fetch(
    `https://api.github.com/repos/${repo}/branches?per_page=100`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
      },
      next: { revalidate: 60 },
    }
  );

  if (!res.ok) {
    const error = await res.text();
    throw new Error(`GitHub API error for ${repo}: ${res.status} - ${error}`);
  }

  const branches = await res.json();

  return branches.map((branch: Record<string, unknown>) => ({
    name: branch.name,
    repo,
  }));
}

export async function GET() {
  const token = process.env.GITHUB_TOKEN;

  if (!token) {
    return NextResponse.json(
      { error: 'GITHUB_TOKEN is not configured' },
      { status: 500 }
    );
  }

  try {
    const results = await Promise.allSettled(
      REPOS.map((repo) => fetchBranches(repo, token))
    );

    const branches: Record<string, unknown[]> = {};
    let total = 0;

    results.forEach((result, index) => {
      const repoName = REPOS[index];
      const key = repoName === 'specimba/nexusalpha' ? 'alpha' : 'dashboards';
      if (result.status === 'fulfilled') {
        branches[key] = result.value;
        total += result.value.length;
      } else {
        branches[key] = [];
      }
    });

    return NextResponse.json({ branches, total });
  } catch (error) {
    return NextResponse.json(
      {
        error: 'Failed to fetch branches',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}
