import { NextRequest, NextResponse } from 'next/server';

const REPO_MAP: Record<string, string> = {
  alpha: 'specimba/nexusalpha',
  dashboards: 'specimba/nexusdashboards',
};

async function fetchCommits(repo: string, token: string) {
  const res = await fetch(
    `https://api.github.com/repos/${repo}/commits?per_page=30`,
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

  const commits = await res.json();

  return commits.map((commit: Record<string, unknown>) => {
    const commitData = commit.commit as Record<string, unknown>;
    const author = commitData?.author as Record<string, unknown> | undefined;
    return {
      sha: (commit.sha as string)?.slice(0, 7) ?? '',
      message: (commitData?.message as string)?.split('\n')[0] ?? '',
      author: (author?.name as string) ?? 'unknown',
      date: (author?.date as string) ?? '',
      html_url: commit.html_url,
      repo,
    };
  });
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
      targetRepos.map(({ fullName }) => fetchCommits(fullName, token))
    );

    const commits: Record<string, unknown[]> = {};
    let total = 0;

    results.forEach((result, index) => {
      const { key } = targetRepos[index];
      if (result.status === 'fulfilled') {
        commits[key] = result.value;
        total += result.value.length;
      } else {
        commits[key] = [];
      }
    });

    return NextResponse.json({ commits, total });
  } catch (error) {
    return NextResponse.json(
      {
        error: 'Failed to fetch commits',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}
