import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { I18nProvider } from "../i18n";
import { AccessibilityProvider } from "../accessibility";
import { OrcaHeader } from "../components/header/OrcaHeader";

// Accessibility Mode is a display mode layered over the existing design (see
// ../accessibility.tsx): it must never change what's shown, only how large
// or high-contrast it renders, and the preference must survive a remount
// (the same "app restart" a real user gets when they reload the page).

const LARGE_TEXT_KEY = "orca.accessibility.largeText";
const HIGH_CONTRAST_KEY = "orca.accessibility.highContrast";

function renderHeader() {
  return render(
    <I18nProvider>
      <AccessibilityProvider>
        <OrcaHeader
          stakeholder="fisherman"
          onStakeholder={() => {}}
          boatClass={null}
          onBoatClass={() => {}}
          health={{ state: "ok", loading: false }}
          latest={null}
          onStartTour={() => {}}
        />
      </AccessibilityProvider>
    </I18nProvider>,
  );
}

afterEach(() => {
  cleanup();
  localStorage.removeItem(LARGE_TEXT_KEY);
  localStorage.removeItem(HIGH_CONTRAST_KEY);
  document.documentElement.removeAttribute("data-large-text");
  document.documentElement.removeAttribute("data-high-contrast");
});

describe("Accessibility mode", () => {
  it("starts with both modes off and neither data attribute set", () => {
    renderHeader();
    expect(document.documentElement.getAttribute("data-large-text")).toBe("false");
    expect(document.documentElement.getAttribute("data-high-contrast")).toBe("false");
    expect(screen.getByRole("button", { name: /large text/i })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });

  it("toggling Large Text sets the data attribute and persists it", async () => {
    renderHeader();
    const toggle = screen.getByRole("button", { name: /large text/i });
    await userEvent.click(toggle);

    expect(toggle).toHaveAttribute("aria-pressed", "true");
    expect(document.documentElement.getAttribute("data-large-text")).toBe("true");
    expect(localStorage.getItem(LARGE_TEXT_KEY)).toBe("1");
  });

  it("toggling High Contrast sets the data attribute independently of Large Text", async () => {
    renderHeader();
    await userEvent.click(screen.getByRole("button", { name: /high contrast/i }));

    expect(document.documentElement.getAttribute("data-high-contrast")).toBe("true");
    expect(document.documentElement.getAttribute("data-large-text")).toBe("false");
    expect(localStorage.getItem(HIGH_CONTRAST_KEY)).toBe("1");
  });

  it("a persisted preference is restored on the next mount (survives a reload)", () => {
    localStorage.setItem(LARGE_TEXT_KEY, "1");
    renderHeader();

    expect(document.documentElement.getAttribute("data-large-text")).toBe("true");
    expect(screen.getByRole("button", { name: /large text/i })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("switching off restores the default (non-large, non-high-contrast) state", async () => {
    localStorage.setItem(LARGE_TEXT_KEY, "1");
    renderHeader();
    const toggle = screen.getByRole("button", { name: /large text/i });
    expect(toggle).toHaveAttribute("aria-pressed", "true");

    await userEvent.click(toggle);

    expect(toggle).toHaveAttribute("aria-pressed", "false");
    expect(document.documentElement.getAttribute("data-large-text")).toBe("false");
    expect(localStorage.getItem(LARGE_TEXT_KEY)).toBe("0");
  });
});
