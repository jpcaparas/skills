export type RuntimeEnvironment = "development" | "test" | "production";

export interface RuntimeDefaults {
  strictRecords?: boolean;
  destructiveCommands?: boolean;
}

export interface RuntimeFramework {
  allowDestructiveCommands(): void;
  enableStrictRecords(): void;
  permitUnstubbedNetworkRequests(): void;
  useMutableDates(): void;
}

export function configureRuntime(
  environment: RuntimeEnvironment,
  defaults: RuntimeDefaults,
  framework: RuntimeFramework,
): void {
  if (defaults.strictRecords ?? true) {
    framework.enableStrictRecords();
  }

  if (environment === "production") {
    framework.allowDestructiveCommands();
  }

  if (environment === "test") {
    framework.permitUnstubbedNetworkRequests();
  }

  framework.useMutableDates();
}
