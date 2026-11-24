import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test } from "@playwright/test";

const DEMO_PASSWORD = "bridge-demo-2026";

async function login(page: Page, email: string, password = DEMO_PASSWORD) {
  await page.goto("/login");
  await page.getByLabel("University email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/dashboard/);
}

test("register, choose a specialization, complete a scenario and get a report", async ({ page }) => {
  const email = `e2e.${Date.now()}@example.com`;
  await page.goto("/register");
  await page.getByLabel("Display name").fill("E2E Student");
  await page.getByLabel("University email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill("e2e-password-123");
  await page.getByLabel("Confirm password").fill("e2e-password-123");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("heading", { name: /Welcome, E2E Student/ })).toBeVisible();

  await page.getByLabel("Specialization").selectOption("international_trade");
  await page.getByRole("button", { name: "Save" }).click();
  await expect(page.getByText("Specialization: International Trade")).toBeVisible();

  await page.goto("/scenarios/delayed-shipment");
  await page.getByRole("button", { name: "Enter the workplace" }).click();
  await expect(page).toHaveURL(/\/sessions\//);

  // Free-text message is interpreted as a workplace action by the (mock) AI and applied by the engine.
  await page.getByRole("tab", { name: "Messages" }).click();
  await page.getByRole("button", { name: /Karim Adel/ }).click();
  await page.getByPlaceholder(/Write to Karim Adel/).fill("Hi Karim, unfortunately the shipment is delayed. I wanted to let you know right away.");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText("Your message was recognised as a workplace action")).toBeVisible();
  await expect(page.getByText("72%")).toBeVisible();

  // A decision with mandatory reasoning.
  await page.getByRole("tab", { name: /Decisions/ }).click();
  const card = page.locator("div").filter({ hasText: /^Request transport quotations/ }).first();
  await card.getByRole("button", { name: "Do this" }).click();
  await expect(page.getByRole("tab", { name: /Decisions/ })).toBeVisible();
  const partial = page.locator("div.rounded-lg").filter({ hasText: "Option B: fly the 6 urgent units" });
  await partial.getByRole("textbox").fill("Only the TC-9 units are urgent; flying pallet 2 keeps us within budget.");
  await partial.getByRole("button", { name: "Do this" }).click();
  await expect(page.getByText(/1,800 EUR/)).toBeVisible();

  // Deliverable.
  await page.getByRole("tab", { name: "Deliverables" }).click();
  await page.getByLabel("Resolution plan for your manager").fill(
    "Situation: three-day delay. Under CIF the seller must ship by the shipment date, so Clause 7 applies. " +
      "Chosen solution: partial air freight of the tension-control pallet for EUR 4,200 within the contingency budget. " +
      "I informed the customer promptly; delivery Thursday. Risks: port congestion; I will monitor and keep a backup. " +
      "Next steps: confirm booking, update the customer, recommend asking Hanseatic to share the cost.",
  );
  await page.getByRole("button", { name: "Submit" }).click();
  await expect(page.getByText("Saved · revision 1")).toBeVisible();

  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: /Finish/ }).click();
  await expect(page).toHaveURL(/\/report$/, { timeout: 30_000 });
  await expect(page.getByText("Scenario outcome")).toBeVisible();
  await expect(page.getByText("Line restarted on time")).toBeVisible();
  await expect(page.getByText("Your key decisions and their consequences")).toBeVisible();

  await page.goto("/profile");
  await expect(page.getByRole("heading", { name: "Competency profile" })).toBeVisible();
  await expect(page.getByText("Low confidence").first()).toBeVisible();
});

test("translation deliverables are right-to-left", async ({ page }) => {
  await login(page, "demo.student@example.com");
  await page.goto("/scenarios/demanding-client");
  await page.getByRole("button", { name: "Enter the workplace" }).click();
  await page.getByRole("tab", { name: "Deliverables" }).click();
  const draft = page.getByLabel("First draft (Arabic)");
  await expect(draft).toHaveAttribute("dir", "rtl");
  await expect(draft).toHaveAttribute("lang", "ar");
});

test("assessment mode has no hints and students cannot open teaching pages", async ({ page }) => {
  await login(page, "demo.student@example.com");
  await page.goto("/scenarios/media-crisis");
  await page.getByLabel("Mode").selectOption("assessment");
  await page.getByRole("button", { name: "Enter the workplace" }).click();
  await expect(page.getByText("Assessment mode")).toBeVisible();
  await expect(page.getByRole("button", { name: "Get a hint" })).toHaveCount(0);
  await page.goto("/teach");
  await expect(page.getByText("Not found")).toBeVisible();
  await page.goto("/admin");
  await expect(page.getByText("Not found")).toBeVisible();
});

test("professor reviews an assessment with a justified correction", async ({ page }) => {
  await login(page, "demo.professor@example.com");
  await page.goto("/teach");
  await page.getByRole("link", { name: /Omar \(demo student\)/ }).first().click();
  await expect(page.getByRole("heading", { name: "Assessment review" })).toBeVisible();
  await page.getByText("Correct this score").first().click();
  await page.getByLabel("New score (0–100)").first().fill("60");
  await page.getByLabel(/Justification \(required/).first().fill("Adjusted after reading the full resolution plan.");
  await page.getByRole("button", { name: "Save correction" }).first().click();
  await expect(page.getByText("Score corrected and recorded.")).toBeVisible();
  await expect(page.getByText("Reviewed by professor").first()).toBeVisible();
});

test("administrator sees usage and settings", async ({ page }) => {
  await login(page, "demo.admin@example.com");
  await page.goto("/admin");
  await expect(page.getByRole("heading", { name: "Administration" })).toBeVisible();
  await expect(page.getByText("AI and platform settings")).toBeVisible();
  await expect(page.getByText("Security and audit log")).toBeVisible();
});

test("key pages have no serious accessibility violations", async ({ page }) => {
  for (const path of ["/", "/login", "/register"]) {
    await page.goto(path);
    const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
    const serious = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    expect(serious.map((v) => `${path}: ${v.id}`)).toEqual([]);
  }
  await login(page, "demo.student@example.com");
  for (const path of ["/dashboard", "/scenarios", "/profile"]) {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
    const serious = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    expect(serious.map((v) => `${path}: ${v.id}`)).toEqual([]);
  }
});
