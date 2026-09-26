import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { I18nProvider } from "../i18n";
import { SosView } from "../components/sos/SosView";

afterEach(() => {
  cleanup();
  window.localStorage.clear();
});

function setGeolocation(success: { latitude: number; longitude: number } | null) {
  Object.defineProperty(window.navigator, "geolocation", {
    configurable: true,
    value: success
      ? {
          getCurrentPosition: (onSuccess: (p: GeolocationPosition) => void) => {
            onSuccess({
              coords: { latitude: success.latitude, longitude: success.longitude, accuracy: 15 },
            } as GeolocationPosition);
          },
        }
      : undefined,
  });
}

function mount() {
  return render(
    <I18nProvider>
      <SosView boatClass={null} />
    </I18nProvider>,
  );
}

beforeEach(() => {
  setGeolocation({ latitude: 12.87, longitude: 74.84 });
});

describe("SosView", () => {
  it("shows the distress-category picker with no message until one is chosen", () => {
    mount();
    expect(screen.getByText("Fire on board")).toBeInTheDocument();
    expect(screen.getByText(/select an emergency type/i)).toBeInTheDocument();
  });

  it("generates a MAYDAY script naming the chosen category once selected", async () => {
    mount();
    await userEvent.click(screen.getByText("Fire on board"));
    const text = screen.getByText(/MAYDAY MAYDAY MAYDAY/);
    expect(text.textContent).toMatch(/FIRE ON BOARD/);
    expect(text.textContent).toMatch(/REQUIRE IMMEDIATE ASSISTANCE/);
  });

  it("includes the live GPS position once acquired, honestly says unknown before that", async () => {
    setGeolocation(null);
    mount();
    await userEvent.click(screen.getByText("Collision"));
    expect(screen.getByText(/MAYDAY MAYDAY MAYDAY/).textContent).toMatch(/POSITION IS UNKNOWN/);
  });

  it("never fabricates coordinates - uses the real acquired position", async () => {
    mount();
    await userEvent.click(screen.getByText("Collision"));
    await userEvent.click(screen.getByRole("button", { name: /get my position/i }));
    const text = await screen.findByText(/MAYDAY MAYDAY MAYDAY/);
    expect(text.textContent).toMatch(/12°52'12"N/);
  });

  it("includes vessel name and persons aboard when provided", async () => {
    mount();
    await userEvent.click(screen.getByText("Medical emergency"));
    await userEvent.type(screen.getByLabelText(/vessel name/i), "Test Boat");
    await userEvent.type(screen.getByLabelText(/persons on board/i), "4");
    const text = screen.getByText(/MAYDAY MAYDAY MAYDAY/);
    expect(text.textContent).toMatch(/TEST BOAT/);
    expect(text.textContent).toMatch(/4 PERSONS ON BOARD/);
  });

  it("the Coast Guard call action targets the real toll-free helpline", async () => {
    mount();
    await userEvent.click(screen.getByText("Fire on board"));
    const callLink = screen.getByRole("link", { name: /call coast guard/i });
    expect(callLink).toHaveAttribute("href", "tel:1554");
  });

  it("never claims to have sent or dispatched anything itself", async () => {
    mount();
    await userEvent.click(screen.getByText("Fire on board"));
    expect(screen.queryByText(/alerting nearby vessels/i)).toBeNull();
    expect(screen.queryByText(/dispatched/i)).toBeNull();
    expect(screen.getByText(/does not contact anyone automatically/i)).toBeInTheDocument();
  });

  it("copies the generated text to the clipboard", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
    mount();
    await userEvent.click(screen.getByText("Fire on board"));
    await userEvent.click(screen.getByRole("button", { name: /copy text/i }));
    expect(writeText).toHaveBeenCalledWith(expect.stringMatching(/MAYDAY MAYDAY MAYDAY/));
    expect(await screen.findByText("Copied")).toBeInTheDocument();
  });

  it("persists the pre-departure checklist across remounts", async () => {
    const { unmount } = mount();
    await userEvent.click(screen.getByLabelText(/EPIRB/i));
    unmount();
    mount();
    expect((screen.getByLabelText(/EPIRB/i) as HTMLInputElement).checked).toBe(true);
  });
});
