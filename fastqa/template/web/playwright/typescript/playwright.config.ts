import { PlaywrightTestConfig, devices } from '@playwright/test';
import { AzureReporterOptions } from '@alex_neo/playwright-azure-reporter/dist/playwright-azure-reporter';
import dotenv from 'dotenv';
dotenv.config();

const config: PlaywrightTestConfig = {
  testDir: "./tests",
  fullyParallel: false,
  timeout: 60 * 1000,
  expect: { timeout: 30 * 1000 },
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 8,
  reporter: [
        ["line"], 
        [
          '@alex_neo/playwright-azure-reporter',
          {
            orgUrl: 'https://dev.azure.com/O2M-QA',
            token: `${process.env.TOKEN}`,
            planId: 300,
            projectName: 'Technical-Patterns',
            environment: 'Windows 10',
            logging: true,
            testRunTitle: 'Playwright Test Run',
            publishTestResultsMode: 'testResult',//'testRun',
            uploadAttachments: true,
            attachmentsType: ['screenshot', 'video', 'trace'],
            testRunConfig: {
              owner: {
                displayName: 'Lennon Avena',
              },
              comment: 'Playwright Test Run',
              configurationIds: [1],
            },
          } as AzureReporterOptions,
        ],
        ["html", { 
            open: 'never', 
            outputFolder: './target/playwright-report/' 
        }], 
        ["junit", { 
          outputFile: "./target/results.xml" 
        }],
        ['monocart-reporter', { 
          name: "My Test Report",
          outputFile: './target/monocart-reporter/report.html'
        }],
    ],
  use: {
      actionTimeout: 60 * 1000,
      navigationTimeout: 30 * 1000,
      trace: 'on',
      screenshot: 'only-on-failure',
      video: {
        mode: 'on'
      },
      ignoreHTTPSErrors: true,
      headless: false,
      viewport: { width: 1400, height: 1050 },
      launchOptions: {
          slowMo: 500,
      },
    },


  /* Configure projects for major browsers */
  projects: [
    // {
    //   name: "DEV",
    //   use: { ...devices["Desktop Chrome"] },
      
    // },
    {
      name: "HML",
      use: { ...devices["Desktop Chrome"],
        // contextOptions: {
        //     screen: {
        //         width: 1400,
        //         height: 1050
        //     }
        // },
        // viewport: {
        //     width: 1400,
        //     height: 1050
        // }
     }
    }
  ],
};
export default config;