*** Settings ***
Resource    ../../resources/common_keywords.resource

*** Variables ***
${LOGIN_PAGE_URL}    http://172.21.166.115/washtabui/login?data=undefined
${HOME_PAGE_URL}     http://172.21.166.115/washtabui/home
${LOGIN_PATH_FRAGMENT}    /washtabui/login
${HOME_PATH_FRAGMENT}     /washtabui/home
${VALID_USERNAME}    hacklarr
${VALID_PASSWORD}    Icstunnel1
${INVALID_USERNAME}  invaliduser
${INVALID_PASSWORD}  incorrectPassword
${USERNAME_TEXTBOX}          xpath=//input[@name='ion-input-0']
${PASSWORD_TEXTBOX}          id=password
${SIGN_IN_BUTTON}            xpath=//ion-button[normalize-space()='SIGN IN']
${HOME_NAVIGATION_BUTTON}    xpath=//ion-fab-button[.//ion-icon[@aria-label='home'] or normalize-space()='home']
${BACK_NAVIGATION_BUTTON}    xpath=//ion-fab-button[.//ion-icon[@aria-label='arrow back'] or normalize-space()='arrow back']

*** Keywords ***
Open Login Page
    [Documentation]    Navigate to the login page.
    Go To    ${LOGIN_PAGE_URL}

Verify Login Page Loaded
    [Documentation]    Verifies login page URL and required login controls are visible.
    Location Should Contain    ${LOGIN_PATH_FRAGMENT}
    Wait For Element To Be Ready    ${USERNAME_TEXTBOX}
    Wait For Element To Be Ready    ${PASSWORD_TEXTBOX}
    Wait For Element To Be Ready    ${SIGN_IN_BUTTON}
    Wait For Element To Be Ready    ${HOME_NAVIGATION_BUTTON}
    Wait For Element To Be Ready    ${BACK_NAVIGATION_BUTTON}

Enter Username
    [Documentation]    Enter username into the username textbox.
    [Arguments]    ${username}
    Input Text When Ready    ${USERNAME_TEXTBOX}    ${username}

Enter Password
    [Documentation]    Enter password into the password textbox.
    [Arguments]    ${password}
    Wait For Element To Be Ready    ${PASSWORD_TEXTBOX}
    Clear Element Text    ${PASSWORD_TEXTBOX}
    Input Password    ${PASSWORD_TEXTBOX}    ${password}

Click Sign In Button
    [Documentation]    Click the SIGN IN button.
    Click When Ready    ${SIGN_IN_BUTTON}

Click Home Navigation Button
    [Documentation]    Click the home navigation button.
    Click When Ready    ${HOME_NAVIGATION_BUTTON}

Click Back Navigation Button
    [Documentation]    Click the back navigation button.
    Click When Ready    ${BACK_NAVIGATION_BUTTON}

Login With Credentials
    [Documentation]    Perform login using provided username and password.
    [Arguments]    ${username}    ${password}
    Enter Username    ${username}
    Enter Password    ${password}
    Click Sign In Button

Login With Valid Credentials
    [Documentation]    Perform login using predefined valid credentials.
    Login With Credentials    ${VALID_USERNAME}    ${VALID_PASSWORD}

Verify Successful Login Redirect
    [Documentation]    Verifies successful authentication redirects the user to the home page.
    Wait Until Location Contains    ${HOME_PATH_FRAGMENT}    10s
    Location Should Contain    ${HOME_PATH_FRAGMENT}

Verify Login Failed And Still On Login Page
    [Documentation]    Verifies authentication failure keeps the user on the login page.
    Location Should Contain    ${LOGIN_PATH_FRAGMENT}
    Wait For Element To Be Ready    ${SIGN_IN_BUTTON}

Verify Password Field Is Masked
    [Documentation]    Verifies that the password field masks entered characters.
    Wait For Element To Be Ready    ${PASSWORD_TEXTBOX}
    ${type}=    Get Element Attribute    ${PASSWORD_TEXTBOX}    type
    Should Be Equal    ${type}    password

Verify Username Required Validation
    [Documentation]    Verifies login submission without username keeps the user on the login page.
    Location Should Contain    ${LOGIN_PATH_FRAGMENT}
    Wait For Element To Be Ready    ${USERNAME_TEXTBOX}

Verify Password Required Validation
    [Documentation]    Verifies login submission without password keeps the user on the login page.
    Location Should Contain    ${LOGIN_PATH_FRAGMENT}
    Wait For Element To Be Ready    ${PASSWORD_TEXTBOX}
