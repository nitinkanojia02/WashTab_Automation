*** Settings ***
Resource    ../../resources/common_keywords.resource

*** Variables ***
${USERNAME_TEXTBOX}    xpath=//input[@name='ion-input-0']
${PASSWORD_TEXTBOX}    id=password
${SIGN_IN_BUTTON}    xpath=//ion-button[normalize-space()='SIGN IN']
${BACK_NAVIGATION_BUTTON}    xpath=(//ion-fab-button)[1]
${HOME_NAVIGATION_BUTTON}    xpath=(//ion-fab-button)[last()]
${LOGIN_PATH_FRAGMENT}    /washtabui/login
${HOME_PATH_FRAGMENT}    /washtabui/home

*** Keywords ***
Verify Login Page Loaded
    [Documentation]    Verifies that the login page is loaded and core controls are visible and ready.
    Location Should Contain    ${LOGIN_PATH_FRAGMENT}
    Wait For Element To Be Ready    ${USERNAME_TEXTBOX}
    Wait For Element To Be Ready    ${PASSWORD_TEXTBOX}
    Wait For Element To Be Ready    ${SIGN_IN_BUTTON}
    Wait For Element To Be Ready    ${BACK_NAVIGATION_BUTTON}
    Wait For Element To Be Ready    ${HOME_NAVIGATION_BUTTON}

Verify Navigation Buttons Visible
    [Documentation]    Verifies that back and home navigation buttons are visible on the login page.
    Wait For Element To Be Ready    ${BACK_NAVIGATION_BUTTON}
    Wait For Element To Be Ready    ${HOME_NAVIGATION_BUTTON}

Enter Username
    [Documentation]    Enters the provided username into the username textbox.
    [Arguments]    ${username}
    Input Text When Ready    ${USERNAME_TEXTBOX}    ${username}

Enter Password
    [Documentation]    Enters the provided password into the password textbox.
    [Arguments]    ${password}
    Input Text When Ready    ${PASSWORD_TEXTBOX}    ${password}

Click Sign In Button
    [Documentation]    Clicks the Sign In button on the login page.
    Click When Ready    ${SIGN_IN_BUTTON}

Click Back Navigation Button
    [Documentation]    Clicks the back navigation control.
    Click When Ready    ${BACK_NAVIGATION_BUTTON}

Click Home Navigation Button
    [Documentation]    Clicks the home navigation control.
    Click When Ready    ${HOME_NAVIGATION_BUTTON}

Perform Login
    [Documentation]    Performs login using the provided username and password.
    [Arguments]    ${username}    ${password}
    Enter Username    ${username}
    Enter Password    ${password}
    Click Sign In Button

Verify Successful Login Redirect
    [Documentation]    Verifies that authentication succeeded and the browser redirects to the home page.
    Wait Until Location Contains    ${HOME_PATH_FRAGMENT}    10s

Verify Login Failed And Still On Login Page
    [Documentation]    Verifies that authentication failed and the user remains on the login page.
    Location Should Contain    ${LOGIN_PATH_FRAGMENT}
    Wait For Element To Be Ready    ${SIGN_IN_BUTTON}

Verify Password Field Is Masked
    [Documentation]    Verifies that the password field masks entered characters.
    ${type}=    Get Element Attribute    ${PASSWORD_TEXTBOX}    type
    Should Be Equal    ${type}    password