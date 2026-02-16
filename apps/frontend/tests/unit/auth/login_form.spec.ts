import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import LoginForm from "@/features/auth/components/login_form.vue";

describe("login_form", () => {
  it("requires email and password", async () => {
    const wrapper = mount(LoginForm, {
      props: {
        isSubmitting: false,
        errorMessage: null,
      },
    });

    await wrapper.find("form").trigger("submit.prevent");

    expect(wrapper.text()).toContain("Email and password are required.");
    expect(wrapper.emitted("submit")).toBeUndefined();
  });

  it("emits submit payload and clears password field", async () => {
    const wrapper = mount(LoginForm, {
      props: {
        isSubmitting: false,
        errorMessage: null,
      },
    });

    await wrapper.find('input[name="email"]').setValue("customer@example.com");
    await wrapper.find('input[name="password"]').setValue("secret");
    await wrapper.find("form").trigger("submit.prevent");

    expect(wrapper.emitted("submit")).toEqual([
      [{ email: "customer@example.com", password: "secret" }],
    ]);

    const passwordInput = wrapper.find('input[name="password"]').element as HTMLInputElement;
    expect(passwordInput.value).toBe("");
  });

  it("disables submit while request is in flight", () => {
    const wrapper = mount(LoginForm, {
      props: {
        isSubmitting: true,
        errorMessage: null,
      },
    });

    const submitButton = wrapper.find('button[type="submit"]').element as HTMLButtonElement;
    expect(submitButton.disabled).toBe(true);
  });
});
