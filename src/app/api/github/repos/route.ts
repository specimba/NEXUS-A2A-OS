import { NextResponse } from 'next/server';

const REPOS = ['specimba/nexusalpha', 'specimba/nexusdashboards'];

async function fetchRepo(repo: string, token: string) {
  const res = await fetch(`https://api.github.com/repos/${repo}`, {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
    },
    next: { revalidate: 60 },
  });

  if (!res.ok) {
    const error = await res.text();
    throw new Error(`GitHub API error for ${repo}: ${res.status} - ${error}`);
  }

  const data = await res.json();

  return {
    name: data.name,
    full_name: data.full_name,
    description: data.description,
    language: data.language,
    stars: data.stargazers_count,
    forks: data.forks_count,
    open_issues: data.open_issues_count,
    topics: data.topics ?? [],
    updated_at: data.updated_at,
    pushed_at: data.pushed_at,
    private: data.private,
    default_branch: data.default_branch,
    visibility: data.visibility,
    html_url: data.html_url,
  };
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
      REPOS.map((repo) => fetchRepo(repo, token))
    );

    const repos = results.map((result, index) => {
      if (result.status === 'fulfilled') {
        return { repo: REPOS[index], success: true, data: result.value };
      }
      return {
        repo: REPOS[index],
        success: false,
        error: result.reason?.message ?? 'Unknown error',
      };
    });

    return NextResponse.json({ repos });
  } catch (error) {
    return NextResponse.json(
      {
        error: 'Failed to fetch repository data',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}
