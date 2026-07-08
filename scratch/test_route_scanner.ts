import { GET } from '../src/app/api/archivist/route';

async function test() {
    console.log("Running route.ts GET handler test...");
    const response = await GET();
    const data = await response.json();
    console.log("Integrity Fields counts:");
    console.log(data.integrityFields);
    console.log("Release Readiness status:");
    console.log(data.releaseReadiness);
}

test().catch(console.error);
