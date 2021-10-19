import { PfeRoutes } from "@kount/yodalib_ui_cypress_8/dist/pfe/portal/pfeRoutes";
import { AdminPageActions } from "@kount/yodalib_ui_cypress_8/dist/pfe/portal/ui/actions/adminPageActions";
import { DashboardPageActions } from "@kount/yodalib_ui_cypress_8/dist/pfe/portal/ui/actions/dashboardPageActions";
import { EditUserPageActions } from "@kount/yodalib_ui_cypress_8/dist/pfe/portal/ui/actions/editUserPageActions";
import { LockUnlockModalActions } from "@kount/yodalib_ui_cypress_8/dist/pfe/portal/ui/actions/lockUnlockModalActions";
import "cypress-xpath";
import * as faker from "faker";
import * as randomatic from "randomatic";
import * as clientMessage from "../../../fixtures/messages/clientManagementMessage.json";
import * as modalMessage from "../../../fixtures/messages/modalMessages.json";
import * as userManagementDetails from "../../../fixtures/users/userManagement.json";
import { ClientManagementHelper } from "../../../helpers/clientManagementHelper";
import { LoginHelper } from "../../../helpers/loginHelper";
import { TestHelper } from "../../../src/TestHelper";

describe("Portal Edit User Page", () => {
    let env: any;
    let firstName: string;
    let lastName: string;
    let adminPage: AdminPageActions;
    let dashboardPage: DashboardPageActions;
    let editUserPage: EditUserPageActions;
    const clientManagementHelper: ClientManagementHelper = new ClientManagementHelper();
    const loginHelper: LoginHelper = new LoginHelper();
    const lockUnlockModal: LockUnlockModalActions = new LockUnlockModalActions();
    const pfeRoutes: PfeRoutes = new PfeRoutes();
    const userName: string = "Automation Test" + randomatic("?", 1, { chars: "BCDGHIJ" });
    const randomPhoneNumber: string = faker.random.number({ min: 1000000000, max: 9999999999 }).toString();
    const invalidPhoneNumber: string = faker.random.number({ min: 100000, max: 999999 }).toString() + randomPhoneNumber;
    const randomFirstName: string = faker.name.firstName();
    const randomLastName: string = faker.name.lastName();

    before(() => {
        loginHelper.login(userManagementDetails.email);
        env = new TestHelper().parseEnv(Cypress.env());
        adminPage = AdminPageActions.fromCypressEnv(env);
        dashboardPage = DashboardPageActions.fromCypressEnv(env);
        editUserPage = EditUserPageActions.fromCypressEnv(env);
    });

    describe("Valid actions", () => {
        beforeEach(() => {
            loginHelper.preserveStorage();
            dashboardPage.navigationItemAdmin().click();
            cy.url().should("include", adminPage.path);
        });

        it("should navigate to admin page, when clicked on All Users link on edit user page", () => {
            pfeRoutes.setupRouteForGetUser();
            clientManagementHelper.navigateToEditUserPage();
            pfeRoutes.verifyGetUser();
            editUserPage.getAllUsers().click().then(() => {
                cy.url().should("include", adminPage.path);
            });
        });

        it("should be able to lock the user, and Unlock the user", () => {
            pfeRoutes.setupRouteForEditUser();
            clientManagementHelper.navigateToEditUserPage();
            editUserPage.lockButton().should("be.enabled").click();
            editUserPage.getFirstNameField().invoke("text").then($firstName => {
                firstName = $firstName;
                editUserPage.getLastNameField().invoke("text").then($lastName => {
                    lastName = $lastName;
                    lockUnlockModal.verifyTitle("Lock " + firstName + " " + lastName);
                });
            });
            lockUnlockModal.verifyMessage(modalMessage.lockMessage);
            lockUnlockModal.lockUserButton().click();
            pfeRoutes.verifyEditUser();

            // Unlock the user
            editUserPage.unlockButton().should("be.enabled").click();
            editUserPage.getFirstNameField().invoke("text").then($firstName => {
                firstName = $firstName;
                editUserPage.getLastNameField().invoke("text").then($lastName => {
                    lastName = $lastName;
                    lockUnlockModal.verifyTitle("Unlock " + firstName + " " + lastName);
                });
            });
            lockUnlockModal.verifyMessage(modalMessage.unlockMessage);
            lockUnlockModal.unlockUserButton().click();
            pfeRoutes.verifyEditUser();
        });

        it("Cancel and Save button should be enabled once role is changed", () => {
            clientManagementHelper.navigateToEditUserPage();
            editUserPage.getViewOnlyFilter().click().then(() => {
                editUserPage.saveUserButton().should("be.enabled");
                editUserPage.cancelButton().should("be.enabled").click();
            });
        });

        it("should be able to edit user details on edit user page", () => {
            pfeRoutes.setupRouteForPostEvents();
            pfeRoutes.setupRouteForEditUser();
            pfeRoutes.waitForPostEvents();
            cy.contains(userName).click();
            cy.url().should("include", editUserPage.path);
            editUserPage.cancelButton().should("be.disabled");
            editUserPage.saveUserButton().should("be.disabled");

            editUserPage.getFirstNameField().then($firstName => {
                firstName = $firstName.text();

                editUserPage.editUserDetailsButton().click();
                editUserPage.getFirstNameField().clear();
                editUserPage.getFirstNameField().type(randomFirstName);
                editUserPage.saveIcon().click();

                pfeRoutes.verifyEditUser();
                editUserPage.saveIcon().should("not.exist");

                editUserPage.editUserDetailsButton().click();
                editUserPage.getFirstNameField().clear();
                editUserPage.getFirstNameField().type(firstName);
                editUserPage.saveIcon().click();

                pfeRoutes.verifyEditUser();
            });

            editUserPage.getLastNameField().then($lastName => {
                lastName = $lastName.text();

                editUserPage.editUserDetailsButton().click();
                editUserPage.getLastNameField().clear();
                editUserPage.getLastNameField().type(randomLastName);
                editUserPage.saveIcon().click();
                pfeRoutes.verifyEditUser();

                editUserPage.saveIcon().should("not.exist");
                editUserPage.editUserDetailsButton().click();
                editUserPage.getLastNameField().clear();
                editUserPage.getLastNameField().type(lastName);
                editUserPage.saveIcon().click();

                pfeRoutes.verifyEditUser();
                editUserPage.saveIcon().should("not.exist");
            });

        });

    });

    describe("Invalid actions", () => {
        beforeEach(() => {
            loginHelper.preserveStorage();
            pfeRoutes.setupRouteForPostEvents();
            dashboardPage.navigationItemAdmin().click();
            cy.url().should("include", adminPage.path);
            clientManagementHelper.navigateToEditUserPage();
            pfeRoutes.waitForPostEvents();
            cy.wait(500);
        });

        it("should provide Error message when Special characters used in FirstName", () => {
            editUserPage.editUserDetailsButton().click();
            editUserPage.getFirstNameField().clear();
            editUserPage.getFirstNameField().type("@//#").then(() => {
                editUserPage.saveUserButton().should("be.disabled");
                editUserPage.getInputFieldError().invoke('text')
                .should('contain', clientMessage.invalidFirstNameMessage);
                editUserPage.saveIcon().should("be.disabled");
            });
            editUserPage.cancelIcon().should("be.enabled").click();
        });

        it("should provide Error message when Special characters used in LastName", () => {
            editUserPage.editUserDetailsButton().click();
            editUserPage.getLastNameField().clear();
            editUserPage.getLastNameField().type("$%").then(() => {
                editUserPage.saveUserButton().should("be.disabled");
                editUserPage.getInputFieldError().invoke('text')
                .should('contain', clientMessage.invalidLastNameMessage);
                editUserPage.saveIcon().should("be.disabled");
            });
            editUserPage.cancelIcon().should("be.enabled").click();
        });

        it("should only allow valid Email Address", () => {
            editUserPage.editUserDetailsButton().click();
            editUserPage.getEmailField().clear();
            editUserPage.getEmailField().type(".%$").then(() => {
                editUserPage.getInputFieldError()
                    .contains(clientMessage.invalidEmailMessage);
                editUserPage.saveIcon().should("be.disabled");
            });
            editUserPage.cancelIcon().should("be.enabled").click();
        });

        it("should not allow more than 15 Digits in Phone Number Field", () => {
            editUserPage.editUserDetailsButton().click();
            editUserPage.getPhoneNumberField().clear();
            editUserPage.getPhoneNumberField().type(invalidPhoneNumber).then(() => {
                editUserPage.getInputFieldError().invoke('text')
                .should('contain', clientMessage.invalidPhoneNumberMessage);
                editUserPage.saveIcon().should("be.disabled");
            });
            editUserPage.cancelIcon().should("be.enabled").click();
        });
    });
});
