import { act, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Clock } from "./clock";

describe("Clock", () => {
  afterEach(() => vi.useRealTimers());
  it("shows the current Fortaleza time", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-08-25T12:30:00Z"));
    render(<Clock />);
    act(() => vi.advanceTimersByTime(1));
    expect(screen.getByText("09:30")).toBeInTheDocument();
    expect(screen.getByText("Fortaleza")).toBeInTheDocument();
  });
});
