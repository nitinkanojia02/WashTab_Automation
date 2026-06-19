*** Settings ***
Resource    ../../resources/common_keywords.resource

*** Variables ***
${LOGIN_PAGE_URL}           http://172.21.166.115/washtabui/login?data=undefined
${HOME_PAGE_URL}            http://172.21.166.115/washtabui/home
${LOGIN_PATH_FRAGMENT}      /washtabui/login
${HOME_PATH_FRAGMENT}       /washtabui/home
${VALID_USERNAME}           haklarr
${VALID_PASSWORD}           Icstunnel1
${INVALID_USERNAME}         wronguser
${INVALID_PASSWORD}         WrongPassword123
${INVALID_PASSWORD_CASE}    icstunnel1
${SPECIAL_CHAR_USERNAME}    user!@#
${LONG_USERNAME_SAMPLE}     aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
${USERNAME_WITH_SPACES}        haklarr
${WHITESPACE_ONLY_VALUE}
${USERNAME_FIELD}          xpath=//input[@aria-labelledby='ion-input-0-lbl']
${PASSWORD_FIELD}          id=password
${SIGN_IN_BUTTON}          xpath=//ion-button[normalize-space(.)='SIGN IN']
${HOME_NAVIGATION_BUTTON}  xpath=(//ion-fab-button)[last()]
${BACK_NAVIGATION_BUTTON}  xpath=(//ion-fab-button)[1]

*** Keywords ***
Open Login Page
    [Documentation]    Opens the login page using the configured login page URL.
    Open Browser To Url    ${LOGIN_PAGE_URL}

Verify Login Form Loaded
    [Documentation]    Verifies that the login form fields and sign-in action are visible and ready for interaction.
    Wait For Element To Be Ready    ${USERNAME_FIELD}
    Wait For Element To Be Ready    ${PASSWORD_FIELD}
    Wait For Element To Be Ready    ${SIGN_IN_BUTTON}

Verify Login Navigation Controls Visible
    [Documentation]    Verifies that navigation controls available on the login page are visible.
    Wait For Element To Be Ready    ${HOME_NAVIGATION_BUTTON}
    Wait For Element To Be Ready    ${BACK_NAVIGATION_BUTTON}

Verify Login Page Ready
    [Documentation]    Verifies that the login page UI is fully loaded and ready for interaction.
    Location Should Contain    ${LOGIN_PATH_FRAGMENT}
    Verify Login Form Loaded
    Verify Login Navigation Controls Visible

Verify Login Page Url
    [Documentation]    Verifies that the browser is currently on the login page.
    Location Should Contain    ${LOGIN_PATH_FRAGMENT}

Enter Username
    [Documentation]    Enters the provided username into the User Name field.
    [Arguments]    ${username}
    Input Text When Ready    ${USERNAME_FIELD}    ${username}

Enter Password
    [Documentation]    Enters the provided password into the Password field.
    [Arguments]    ${password}
    Input Text When Ready    ${PASSWORD_FIELD}    ${password}

Submit Login Form
    [Documentation]    Submits the login form using the Sign In button.
    Click When Ready    ${SIGN_IN_BUTTON}

Login With Credentials
    [Documentation]    Performs a login attempt using the provided username and password.
    [Arguments]    ${username}    ${password}
    Enter Username    ${username}
    Enter Password    ${password}
    Submit Login Form

Login With Valid Credentials
    [Documentation]    Performs login using the configured valid credentials.
    Login With Credentials    ${VALID_USERNAME}    ${VALID_PASSWORD}

Click Home Navigation Button
    [Documentation]    Navigates to the home page using the Home navigation control.
    Click When Ready    ${HOME_NAVIGATION_BUTTON}

Click Back Navigation Button
    [Documentation]    Navigates using the Back navigation control.
    Click When Ready    ${BACK_NAVIGATION_BUTTON}

Verify Login Failed And Still On Login Page
    [Documentation]    Verifies that login was rejected and the user remains on the login page.
    Location Should Contain    ${LOGIN_PATH_FRAGMENT}
    Wait For Element To Be Ready    ${USERNAME_FIELD}
    Wait For Element To Be Ready    ${SIGN_IN_BUTTON}

Verify Successful Login Redirect
    [Documentation]    Verifies that authentication succeeded and the user is redirected to the home page.
    Location Should Contain    ${HOME_PATH_FRAGMENT}

Verify Password Field Is Masked
    [Documentation]    Verifies that the password field masks entered characters.
    ${type}=    Get Element Attribute    ${PASSWORD_FIELD}    type
    Should Be Equal    ${type}    password
