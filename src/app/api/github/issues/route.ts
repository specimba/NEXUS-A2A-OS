import { NextResponse } from 'next/server';

const REPOS = ['specimba/nexusalpha', 'specimba/nexusdashboards'];

async function fetchIssues(repo: string, token: string) {
  const res = await fetch(
    `https://api.github.com/repos/${repo}/issues?state=open&per_page=50`,
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

  const issues = await res.json();

  // Filter out pull requests — GitHub API returns PRs in the issues endpoint
  return issues
    .filter((issue: Record<string, unknown>) => !issue.pull_request)
    .map((issue: Record<string, unknown>) => ({
      number: issue.number,
      title: issue.title,
      state: issue.state,
      created_at: issue.created_at,
      labels: Array.isArray(issue.labels)
        ? (issue.labels as Array<Record<string, unknown>>).map((label) => ({
            name: label.name,
            color: label.color,
          }))
        : [],
      assignees: Array.isArray(issue.assignees)
        ? (issue.assignees as Array<Record<string, string>>).map(
            (assignee) => ({
              login: assignee.login,
              avatar_url: assignee.avatar_url,
            })
          )
        : [],
      html_url: issue.html_url,
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
      REPOS.map((repo) => fetchIssues(repo, token))
    );

    const issues: Record<string, unknown[]> = {};
    let total = 0;

    results.forEach((result, index) => {
      const repoName = REPOS[index];
      const key = repoName === 'specimba/nexusalpha' ? 'alpha' : 'dashboards';
      if (result.status === 'fulfilled') {
        issues[key] = result.value;
        total += result.value.length;
      } else {
        issues[key] = [];
      }
    });

    return NextResponse.json({ issues, total });
  } catch (error) {
    return NextResponse.json(
      {
        error: 'Failed to fetch issues',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}
